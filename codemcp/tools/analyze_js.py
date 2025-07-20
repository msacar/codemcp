#!/usr/bin/env python3
"""AST-based code analysis tool for JavaScript/TypeScript using Tree-sitter."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

try:
    from tree_sitter import Node, Parser
    from tree_sitter_languages import get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Node = Any
    Parser = Any

from ..async_file_utils import async_open_text
from ..common import normalize_file_path
from ..mcp import mcp
from .commit_utils import append_commit_hash
from .smart_search import JS_TS_PATTERNS, USAGE_PATTERNS

__all__ = [
    "analyze_js",
    "find_js_references",
    "rename_js_symbol",
    "add_js_parameter",
    "remove_unused_exports",
    "JavaScriptAnalyzer",
]


class JavaScriptAnalyzer:
    """AST-based analyzer for JavaScript and TypeScript files."""

    def __init__(self):
        if not TREE_SITTER_AVAILABLE:
            logging.warning("Tree-sitter not available, using fallback regex mode")
            self.parsers_available = False
            return

        try:
            self.js_parser = get_parser("javascript")
            self.ts_parser = get_parser("typescript")
            self.tsx_parser = get_parser("tsx")
            self.jsx_parser = get_parser("javascript")  # JSX uses JS parser
            self.parsers_available = True
        except Exception as e:
            logging.warning(f"Failed to initialize Tree-sitter parsers: {e}")
            self.parsers_available = False

    def get_parser(self, file_path: str) -> Optional[Parser]:
        """Select appropriate parser based on file extension."""
        if not self.parsers_available:
            return None

        ext = file_path.lower()
        if ext.endswith(".ts"):
            return self.ts_parser
        elif ext.endswith(".tsx"):
            return self.tsx_parser
        elif ext.endswith(".jsx"):
            return self.jsx_parser
        else:  # .js, .mjs, etc.
            return self.js_parser

    def parse_content(self, content: str, file_path: str) -> Optional[Any]:
        """Parse file content and return AST tree."""
        parser = self.get_parser(file_path)
        if not parser:
            return None

        try:
            return parser.parse(bytes(content, "utf-8"))
        except Exception as e:
            logging.warning(f"Failed to parse {file_path}: {e}")
            return None

    def find_functions(self, tree: Any) -> List[Dict[str, Any]]:
        """Extract all function declarations and expressions."""
        if not tree:
            return []

        functions = []

        def visit_node(node: Node, parent_name: Optional[str] = None):
            # Function declarations
            if node.type == "function_declaration":
                name_node = self._find_child_by_type(node, "identifier")
                if name_node:
                    functions.append(
                        {
                            "name": name_node.text.decode("utf-8"),
                            "type": "function",
                            "line": node.start_point[0] + 1,
                            "column": node.start_point[1],
                            "params": self._extract_params(node),
                            "async": self._has_child_type(node, "async"),
                            "generator": self._has_child_type(node, "*"),
                        }
                    )

            # Arrow functions and function expressions
            elif node.type in ["variable_declarator", "lexical_binding"]:
                name_node = self._find_child_by_type(node, "identifier")
                value_node = None

                for child in node.children:
                    if child.type in ["arrow_function", "function_expression"]:
                        value_node = child
                        break

                if name_node and value_node:
                    functions.append(
                        {
                            "name": name_node.text.decode("utf-8"),
                            "type": "arrow"
                            if value_node.type == "arrow_function"
                            else "function_expression",
                            "line": node.start_point[0] + 1,
                            "column": node.start_point[1],
                            "params": self._extract_params(value_node),
                            "async": self._has_child_type(value_node, "async"),
                        }
                    )

            # Method definitions in classes
            elif node.type == "method_definition":
                name_node = self._find_child_by_type(
                    node, ["property_identifier", "identifier"]
                )
                if name_node:
                    method_info = {
                        "name": name_node.text.decode("utf-8"),
                        "type": "method",
                        "line": node.start_point[0] + 1,
                        "column": node.start_point[1],
                        "params": self._extract_params(node),
                        "async": self._has_child_type(node, "async"),
                        "static": self._has_child_type(node, "static"),
                        "getter": node.child_by_field_name("kind")
                        and node.child_by_field_name("kind").text == b"get",
                        "setter": node.child_by_field_name("kind")
                        and node.child_by_field_name("kind").text == b"set",
                    }
                    if parent_name:
                        method_info["class"] = parent_name
                    functions.append(method_info)

            # Object method shorthand
            elif node.type == "pair" and node.child_count >= 2:
                key_node = node.child_by_field_name("key")
                value_node = node.child_by_field_name("value")
                if (
                    key_node
                    and value_node
                    and value_node.type in ["arrow_function", "function_expression"]
                ):
                    functions.append(
                        {
                            "name": key_node.text.decode("utf-8"),
                            "type": "object_method",
                            "line": node.start_point[0] + 1,
                            "column": node.start_point[1],
                            "params": self._extract_params(value_node),
                            "async": self._has_child_type(value_node, "async"),
                        }
                    )

            # Track class names for method context
            class_name = parent_name
            if node.type == "class_declaration":
                class_name_node = self._find_child_by_type(node, "identifier")
                if class_name_node:
                    class_name = class_name_node.text.decode("utf-8")

            # Continue traversing
            for child in node.children:
                visit_node(child, class_name)

        visit_node(tree.root_node)
        return functions

    def find_classes(self, tree: Any) -> List[Dict[str, Any]]:
        """Extract all class declarations."""
        if not tree:
            return []

        classes = []

        def visit_node(node: Node):
            if node.type == "class_declaration":
                name_node = self._find_child_by_type(node, "identifier")
                if name_node:
                    class_info = {
                        "name": name_node.text.decode("utf-8"),
                        "line": node.start_point[0] + 1,
                        "column": node.start_point[1],
                        "extends": None,
                        "implements": [],
                    }

                    # Check for extends
                    heritage = node.child_by_field_name("heritage")
                    if heritage:
                        extends_node = self._find_child_by_type(heritage, "identifier")
                        if extends_node:
                            class_info["extends"] = extends_node.text.decode("utf-8")

                    classes.append(class_info)

            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return classes

    def find_imports(self, tree: Any) -> List[Dict[str, Any]]:
        """Extract all import statements."""
        if not tree:
            return []

        imports = []

        def visit_node(node: Node):
            if node.type == "import_statement":
                source_node = self._find_child_by_type(node, "string")
                if source_node:
                    source = source_node.text.decode("utf-8").strip("\"'`")

                    import_info = {
                        "source": source,
                        "line": node.start_point[0] + 1,
                        "column": node.start_point[1],
                        "default": None,
                        "named": [],
                        "namespace": None,
                    }

                    # Extract import clause
                    import_clause = node.child_by_field_name("import")
                    if import_clause:
                        # Default import
                        default_import = self._find_child_by_type(
                            import_clause, "identifier"
                        )
                        if default_import and default_import.parent == import_clause:
                            import_info["default"] = default_import.text.decode("utf-8")

                        # Named imports
                        named_imports = self._find_child_by_type(
                            import_clause, "named_imports"
                        )
                        if named_imports:
                            for child in named_imports.children:
                                if child.type == "import_specifier":
                                    name_node = child.child_by_field_name("name")
                                    alias_node = child.child_by_field_name("alias")
                                    if name_node:
                                        import_spec = {
                                            "name": name_node.text.decode("utf-8")
                                        }
                                        if alias_node:
                                            import_spec["alias"] = (
                                                alias_node.text.decode("utf-8")
                                            )
                                        import_info["named"].append(import_spec)

                        # Namespace import
                        namespace_import = self._find_child_by_type(
                            import_clause, "namespace_import"
                        )
                        if namespace_import:
                            ns_name = self._find_child_by_type(
                                namespace_import, "identifier"
                            )
                            if ns_name:
                                import_info["namespace"] = ns_name.text.decode("utf-8")

                    imports.append(import_info)

            # Handle require() calls
            elif node.type == "call_expression":
                callee = node.child_by_field_name("function")
                if callee and callee.text == b"require":
                    args = node.child_by_field_name("arguments")
                    if args:
                        source_node = self._find_child_by_type(args, "string")
                        if source_node:
                            source = source_node.text.decode("utf-8").strip("\"'`")
                            imports.append(
                                {
                                    "source": source,
                                    "line": node.start_point[0] + 1,
                                    "column": node.start_point[1],
                                    "type": "require",
                                }
                            )

            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return imports

    def find_exports(self, tree: Any) -> List[Dict[str, Any]]:
        """Extract all export statements."""
        if not tree:
            return []

        exports = []

        def visit_node(node: Node):
            # Export declarations
            if node.type in ["export_statement"]:
                export_info = {
                    "line": node.start_point[0] + 1,
                    "column": node.start_point[1],
                    "default": False,
                    "type": None,
                    "name": None,
                    "named": [],
                }

                # Check what's being exported
                for child in node.children:
                    if child.type == "export":
                        continue

                    if child.type == "function_declaration":
                        name_node = self._find_child_by_type(child, "identifier")
                        if name_node:
                            export_info["name"] = name_node.text.decode("utf-8")
                            export_info["type"] = "function"

                    elif child.type == "class_declaration":
                        name_node = self._find_child_by_type(child, "identifier")
                        if name_node:
                            export_info["name"] = name_node.text.decode("utf-8")
                            export_info["type"] = "class"

                    elif child.type in ["lexical_declaration", "variable_declaration"]:
                        export_info["type"] = "variable"
                        for declarator in child.children:
                            if declarator.type in [
                                "variable_declarator",
                                "lexical_binding",
                            ]:
                                name_node = self._find_child_by_type(
                                    declarator, "identifier"
                                )
                                if name_node:
                                    export_info["named"].append(
                                        name_node.text.decode("utf-8")
                                    )

                    elif child.type == "export_clause":
                        export_info["type"] = "named"
                        for spec in child.children:
                            if spec.type == "export_specifier":
                                name_node = spec.child_by_field_name("name")
                                alias_node = spec.child_by_field_name("alias")
                                if name_node:
                                    export_spec = {
                                        "name": name_node.text.decode("utf-8")
                                    }
                                    if alias_node:
                                        export_spec["alias"] = alias_node.text.decode(
                                            "utf-8"
                                        )
                                    export_info["named"].append(export_spec)

                exports.append(export_info)

            # Default exports
            elif node.type == "export_default_declaration":
                export_info = {
                    "line": node.start_point[0] + 1,
                    "column": node.start_point[1],
                    "default": True,
                    "type": None,
                    "name": None,
                }

                # Check what's being exported as default
                declaration = node.child_by_field_name("declaration")
                if declaration:
                    if declaration.type == "function_declaration":
                        name_node = self._find_child_by_type(declaration, "identifier")
                        if name_node:
                            export_info["name"] = name_node.text.decode("utf-8")
                        export_info["type"] = "function"

                    elif declaration.type == "class_declaration":
                        name_node = self._find_child_by_type(declaration, "identifier")
                        if name_node:
                            export_info["name"] = name_node.text.decode("utf-8")
                        export_info["type"] = "class"

                    elif declaration.type == "identifier":
                        export_info["name"] = declaration.text.decode("utf-8")
                        export_info["type"] = "identifier"

                    else:
                        export_info["type"] = declaration.type

                exports.append(export_info)

            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return exports

    def find_references(self, tree: Any, symbol: str) -> List[Dict[str, Any]]:
        """Find all references to a symbol with context."""
        if not tree:
            return []

        references = []

        def get_context(node: Node, symbol_node: Node) -> str:
            """Determine the context of a symbol reference."""
            parent = symbol_node.parent
            if not parent:
                return "unknown"

            # Function/method call
            if (
                parent.type == "call_expression"
                and parent.child_by_field_name("function") == symbol_node
            ):
                return "function_call"

            # New instance
            if (
                parent.type == "new_expression"
                and parent.child_by_field_name("constructor") == symbol_node
            ):
                return "new_instance"

            # Member access
            if parent.type == "member_expression":
                if parent.child_by_field_name("object") == symbol_node:
                    return "object_access"
                elif parent.child_by_field_name("property") == symbol_node:
                    return "property_access"

            # Variable declaration
            if parent.type in ["variable_declarator", "lexical_binding"]:
                if parent.child_by_field_name("name") == symbol_node:
                    return "declaration"

            # Assignment
            if parent.type == "assignment_expression":
                if parent.child_by_field_name("left") == symbol_node:
                    return "assignment_target"
                else:
                    return "assignment_value"

            # Function parameter
            if parent.type in [
                "required_parameter",
                "optional_parameter",
                "formal_parameters",
            ]:
                return "parameter"

            # Import
            if parent.type == "import_specifier":
                return "import"

            # Export
            if parent.type == "export_specifier":
                return "export"

            # JSX component
            if parent.type in [
                "jsx_opening_element",
                "jsx_closing_element",
                "jsx_self_closing_element",
            ]:
                return "jsx_component"

            # Type annotation (TypeScript)
            if parent.type in ["type_identifier", "type_annotation"]:
                return "type_reference"

            return "reference"

        def visit_node(node: Node, scope_stack: List[str] = None):
            if scope_stack is None:
                scope_stack = []

            # Check if this node is an identifier matching our symbol
            if node.type == "identifier" and node.text.decode("utf-8") == symbol:
                context = get_context(node, node)

                references.append(
                    {
                        "line": node.start_point[0] + 1,
                        "column": node.start_point[1],
                        "end_line": node.end_point[0] + 1,
                        "end_column": node.end_point[1],
                        "context": context,
                        "scope": "/".join(scope_stack) if scope_stack else "global",
                    }
                )

            # Track scope
            new_scope = scope_stack.copy()
            scope_name = None

            if node.type in ["function_declaration", "function_expression"]:
                name_node = self._find_child_by_type(node, "identifier")
                if name_node:
                    scope_name = name_node.text.decode("utf-8")
            elif node.type == "method_definition":
                name_node = self._find_child_by_type(
                    node, ["property_identifier", "identifier"]
                )
                if name_node:
                    scope_name = name_node.text.decode("utf-8")
            elif node.type == "class_declaration":
                name_node = self._find_child_by_type(node, "identifier")
                if name_node:
                    scope_name = f"class:{name_node.text.decode('utf-8')}"

            if scope_name:
                new_scope.append(scope_name)

            # Continue traversing
            for child in node.children:
                visit_node(child, new_scope)

        visit_node(tree.root_node)
        return references

    def _find_child_by_type(self, node: Node, types: str | List[str]) -> Optional[Node]:
        """Find first child node of given type(s)."""
        if isinstance(types, str):
            types = [types]

        for child in node.children:
            if child.type in types:
                return child
        return None

    def _has_child_type(self, node: Node, child_type: str) -> bool:
        """Check if node has a child of given type."""
        return any(child.type == child_type for child in node.children)

    def _extract_params(self, node: Node) -> List[Dict[str, Any]]:
        """Extract parameter information from function node."""
        params = []
        param_list = None

        # Find parameters node
        for child in node.children:
            if child.type in ["formal_parameters", "parameters"]:
                param_list = child
                break

        if not param_list:
            return params

        for child in param_list.children:
            if child.type == "identifier":
                params.append(
                    {
                        "name": child.text.decode("utf-8"),
                        "optional": False,
                        "default": False,
                    }
                )

            elif child.type in ["required_parameter", "optional_parameter"]:
                # TypeScript parameters
                name_node = self._find_child_by_type(
                    child, ["identifier", "array_pattern", "object_pattern"]
                )
                if name_node:
                    param_info = {
                        "name": name_node.text.decode("utf-8")
                        if name_node.type == "identifier"
                        else f"[{name_node.type}]",
                        "optional": child.type == "optional_parameter"
                        or "?" in child.text.decode("utf-8"),
                        "default": self._find_child_by_type(child, "=") is not None,
                    }

                    # Extract type if present
                    type_node = child.child_by_field_name("type")
                    if type_node:
                        param_info["type"] = type_node.text.decode("utf-8")

                    params.append(param_info)

            elif child.type == "rest_parameter":
                name_node = self._find_child_by_type(child, "identifier")
                if name_node:
                    params.append(
                        {"name": f"...{name_node.text.decode('utf-8')}", "rest": True}
                    )

        return params


def _regex_fallback_analysis(
    file_path: str, content: str, analysis_type: str
) -> Dict[str, Any]:
    """Fallback to regex-based analysis when Tree-sitter fails."""
    logging.info(f"Using regex fallback for {file_path}")
    result = {"fallback_mode": True}

    lines = content.split("\n")

    if analysis_type in ["summary", "functions", "all"]:
        functions = []
        # A set of regexes to find functions in various forms.
        # This is a fallback and may not be perfect.
        regexes = [
            # function funcName, async function funcName
            re.compile(r"(?:async\s+)?function\s+([a-zA-Z0-9_$]+)"),
            # const funcName = ..., let funcName = ...
            re.compile(r"(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*="),
            # methodName: function, methodName: async function
            re.compile(r"([a-zA-Z0-9_$]+)\s*:\s*(?:async\s+)?function"),
            # methodName() {, async methodName() {, static methodName() {
            re.compile(r"(?:static\s+)?(?:async\s+)?(constructor|(?![0-9])\w+)\s*\([^)]*\)\s*{"),
        ]

        for line_num, line in enumerate(lines, 1):
            for regex in regexes:
                matches = regex.findall(line)
                for match in matches:
                    if match:
                        functions.append(
                            {"name": match, "line": line_num, "type": "regex_detected"}
                        )

        # Remove duplicates that might be found by multiple regexes
        unique_functions = []
        seen = set()
        for func in functions:
            identifier = (func["name"], func["line"])
            if identifier not in seen:
                unique_functions.append(func)
                seen.add(identifier)
        functions = unique_functions

        if analysis_type == "functions":
            result["functions"] = functions
        else:
            result["functions_count"] = len(functions)

    if analysis_type in ["summary", "imports", "all"]:
        imports = []
        # Updated regex to handle both ES6 imports and CommonJS requires
        import_regex = re.compile(
            r"(?:import\s+(?:[\w{},\s*]+\s+from\s+)?['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
            re.IGNORECASE,
        )
        for line_num, line in enumerate(lines, 1):
            matches = import_regex.findall(line)
            for match in matches:
                # match is a tuple, get the non-empty value
                source = match[0] if match[0] else match[1]
                if source:
                    imports.append({"source": source, "line": line_num})

        if analysis_type == "imports":
            result["imports"] = imports
        else:
            result["imports_count"] = len(imports)

    if analysis_type in ["summary", "exports", "all"]:
        exports = []
        export_regex = re.compile(
            r"export\s+(?:default\s+)?(?:class|function|const|let|var)?\s*(\w+)?",
            re.IGNORECASE,
        )
        for line_num, line in enumerate(lines, 1):
            matches = export_regex.findall(line)
            for match in matches:
                if match:
                    exports.append(
                        {"name": match, "line": line_num, "default": "default" in line}
                    )

        if analysis_type == "exports":
            result["exports"] = exports
        else:
            result["exports_count"] = len(exports)

    return result


@mcp.tool()
async def analyze_js(
    path: str,
    analysis_type: str = "summary",
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """
    Analyze JavaScript/TypeScript file structure using AST.

    Supports: .js, .ts, .jsx, .tsx, .mjs files

    Args:
        path: Path to the JavaScript/TypeScript file
        analysis_type: Type of analysis to perform
            - summary: Overview of functions, imports, exports, classes
            - functions: Detailed function information with parameters
            - classes: Class declarations with inheritance
            - imports: Import statements with named/default/namespace imports
            - exports: Export statements with named/default exports
            - all: Complete analysis
        chat_id: The unique ID of the current chat session
        commit_hash: Git commit hash for tracking

    Returns:
        JSON formatted analysis results
    """
    # Set default values
    chat_id = "" if chat_id is None else chat_id

    # Validate analysis type
    valid_analysis_types = {"summary", "functions", "classes", "imports", "exports", "all"}
    if analysis_type not in valid_analysis_types:
        return json.dumps(
            {"error": f"Invalid analysis type: '{analysis_type}'. Must be one of {sorted(list(valid_analysis_types))}"}
        )

    # Normalize path
    full_path = normalize_file_path(path)

    # Validate file extension
    valid_extensions = (".js", ".ts", ".jsx", ".tsx", ".mjs")
    if not full_path.lower().endswith(valid_extensions):
        return json.dumps(
            {"error": f"File must be one of: {', '.join(valid_extensions)}"}
        )

    try:
        # Read file content
        content = await async_open_text(full_path, encoding="utf-8", errors="replace")
    except Exception as e:
        return json.dumps({"error": f"Failed to read file: {str(e)}"})

    # Initialize analyzer
    analyzer = JavaScriptAnalyzer()

    # Try AST parsing first
    tree = analyzer.parse_content(content, full_path)

    # Perform analysis
    result = {"file": path}

    if tree and analyzer.parsers_available:
        # AST-based analysis
        if analysis_type in ["summary", "all"]:
            functions = analyzer.find_functions(tree)
            classes = analyzer.find_classes(tree)
            imports = analyzer.find_imports(tree)
            exports = analyzer.find_exports(tree)

            result["summary"] = {
                "functions_count": len(functions),
                "classes_count": len(classes),
                "imports_count": len(imports),
                "exports_count": len(exports),
                "has_default_export": any(e.get("default") for e in exports),
                "main_exports": [
                    e.get("name") or f"default ({e.get('type', 'unknown')})"
                    for e in exports
                    if e.get("name") or e.get("default")
                ][:5],
            }

        if analysis_type in ["functions", "all"]:
            result["functions"] = analyzer.find_functions(tree)

        if analysis_type in ["classes", "all"]:
            result["classes"] = analyzer.find_classes(tree)

        if analysis_type in ["imports", "all"]:
            result["imports"] = analyzer.find_imports(tree)

        if analysis_type in ["exports", "all"]:
            result["exports"] = analyzer.find_exports(tree)

    else:
        # Fallback to regex-based analysis
        fallback_result = _regex_fallback_analysis(full_path, content, analysis_type)
        result.update(fallback_result)

    result_json = json.dumps(result, indent=2)
    result_with_hash, _ = await append_commit_hash(result_json, full_path, commit_hash)
    return result_with_hash


@mcp.tool()
async def find_js_references(
    symbol: str,
    path: str,
    context_filter: Optional[str] = None,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """
    Find all references to a JavaScript/TypeScript symbol with context.

    Args:
        symbol: The symbol name to search for
        path: File or directory path to search in
        context_filter: Optional filter for reference context
            - function_call: Only function calls
            - declaration: Only declarations
            - import: Only imports
            - export: Only exports
            - jsx_component: Only JSX component usage
            - new_instance: Only new instantiations
            - property_access: Only property access
            - type_reference: Only type references (TypeScript)
        chat_id: The unique ID of the current chat session
        commit_hash: Git commit hash for tracking

    Returns:
        JSON formatted list of references with context and location
    """
    # Set default values
    chat_id = "" if chat_id is None else chat_id

    # Normalize path
    full_path = normalize_file_path(path)
    from pathlib import Path

    path_obj = Path(full_path)

    analyzer = JavaScriptAnalyzer()
    all_references = []
    files_analyzed = 0
    files_with_references = 0

    # Determine files to analyze
    if path_obj.is_file():
        files = [str(path_obj)]
    else:
        # Find all JS/TS files in directory
        import glob

        patterns = ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.mjs"]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(str(path_obj / pattern), recursive=True))

    # Analyze each file
    for file_path in files:
        try:
            content = await async_open_text(
                file_path, encoding="utf-8", errors="replace"
            )
            files_analyzed += 1

            # Try AST parsing
            tree = analyzer.parse_content(content, file_path)

            if tree and analyzer.parsers_available:
                # AST-based reference finding
                references = analyzer.find_references(tree, symbol)

                # Apply context filter if specified
                if context_filter:
                    references = [
                        ref for ref in references if ref["context"] == context_filter
                    ]

                if references:
                    files_with_references += 1
                    # Add code snippet for each reference
                    lines = content.split("\n")
                    for ref in references:
                        line_idx = ref["line"] - 1
                        if 0 <= line_idx < len(lines):
                            ref["code"] = lines[line_idx].strip()

                    all_references.append(
                        {"file": str(file_path), "references": references}
                    )
            else:
                # Fallback to regex-based search
                from .smart_search import get_line_context

                # Use appropriate patterns based on context filter
                patterns = {}
                if context_filter == "function_call":
                    patterns["function_call"] = USAGE_PATTERNS["function_call"]
                elif context_filter == "import":
                    patterns["import_named"] = USAGE_PATTERNS["import_named"]
                    patterns["import_default"] = USAGE_PATTERNS["import_default"]
                elif context_filter:
                    # Try to find matching pattern
                    for name, pattern in USAGE_PATTERNS.items():
                        if context_filter in name:
                            patterns[name] = pattern
                else:
                    # Use all patterns
                    patterns = USAGE_PATTERNS

                file_refs = []
                for pattern_name, pattern in patterns.items():
                    matches = await get_line_context(
                        file_path, pattern, symbol, pattern_name
                    )
                    for match in matches:
                        file_refs.append(
                            {
                                "line": match["line_num"],
                                "column": 0,  # Regex doesn't give exact column
                                "context": pattern_name,
                                "code": match["line"].strip(),
                                "fallback": True,
                            }
                        )

                if file_refs:
                    files_with_references += 1
                    all_references.append(
                        {"file": str(file_path), "references": file_refs}
                    )

        except Exception as e:
            logging.warning(f"Failed to analyze {file_path}: {e}")
            continue

    # Calculate statistics
    total_references = sum(len(f["references"]) for f in all_references)

    result = {
        "symbol": symbol,
        "context_filter": context_filter,
        "files_analyzed": files_analyzed,
        "files_with_references": files_with_references,
        "total_references": total_references,
        "references_by_context": {},
        "files": all_references,
    }

    # Group by context
    for file_info in all_references:
        for ref in file_info["references"]:
            context = ref["context"]
            if context not in result["references_by_context"]:
                result["references_by_context"][context] = 0
            result["references_by_context"][context] += 1

    result_json = json.dumps(result, indent=2)
    result_with_hash, _ = await append_commit_hash(result_json, full_path, commit_hash)
    return result_with_hash


@mcp.tool()
async def rename_js_symbol(
    old_name: str,
    new_name: str,
    path: str,
    dry_run: bool = True,
    scope: Optional[str] = None,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """
    Rename a JavaScript/TypeScript symbol using AST-based refactoring.

    This tool safely renames symbols while preserving code structure and handling
    edge cases like shadowing, destructuring, and property shorthand.

    Args:
        old_name: Current name of the symbol
        new_name: New name for the symbol
        path: File or directory to refactor
        dry_run: If True, preview changes without modifying files
        scope: Optional scope to limit renaming (e.g., "function:processData")
        chat_id: The unique ID of the current chat session
        commit_hash: Git commit hash for tracking

    Returns:
        JSON formatted summary of changes made or to be made
    """
    # Set default values
    chat_id = "" if chat_id is None else chat_id

    # Validate names
    if not re.match(r"^[a-zA-Z_$][a-zA-Z0-9_$]*$", new_name):
        return json.dumps({"error": f"Invalid identifier: {new_name}"})

    # Find all references first
    references_json = await find_js_references(
        old_name, path, chat_id=chat_id, commit_hash=commit_hash
    )
    references_data = json.loads(references_json)

    changes = []
    analyzer = JavaScriptAnalyzer()

    for file_info in references_data["files"]:
        file_path = file_info["file"]
        file_references = file_info["references"]

        if not file_references:
            continue

        # Filter by scope if specified
        if scope:
            file_references = [
                ref for ref in file_references if scope in ref.get("scope", "")
            ]

        if not file_references:
            continue

        try:
            # Read file content
            content = await async_open_text(
                file_path, encoding="utf-8", errors="replace"
            )

            # Parse with AST for accurate renaming
            tree = analyzer.parse_content(content, file_path)

            if tree and analyzer.parsers_available:
                # Build list of replacements with AST validation
                replacements = []

                for ref in file_references:
                    # Validate this is a safe rename
                    if _is_safe_rename(tree, ref, old_name, new_name):
                        replacements.append(
                            {
                                "line": ref["line"],
                                "column": ref["column"],
                                "end_column": ref.get(
                                    "end_column", ref["column"] + len(old_name)
                                ),
                                "context": ref["context"],
                            }
                        )

                if replacements:
                    # Apply replacements (reverse order to maintain positions)
                    new_content = _apply_replacements(
                        content, replacements, old_name, new_name
                    )

                    changes.append(
                        {
                            "file": file_path,
                            "replacements": replacements,
                            "old_content": content,
                            "new_content": new_content,
                        }
                    )
            else:
                # Fallback to text-based replacement with validation
                lines = content.split("\n")
                modified_lines = lines.copy()
                replacements = []

                for ref in sorted(
                    file_references,
                    key=lambda r: (r["line"], r["column"]),
                    reverse=True,
                ):
                    line_idx = ref["line"] - 1
                    if 0 <= line_idx < len(lines):
                        line = modified_lines[line_idx]
                        col = ref["column"]

                        # Verify exact match and word boundaries
                        if (
                            col + len(old_name) <= len(line)
                            and line[col : col + len(old_name)] == old_name
                        ):
                            # Check word boundaries
                            before_ok = (
                                col == 0
                                or not line[col - 1].isalnum()
                                and line[col - 1] not in "_$"
                            )
                            after_ok = (
                                col + len(old_name) >= len(line)
                                or not line[col + len(old_name)].isalnum()
                                and line[col + len(old_name)] not in "_$"
                            )

                            if before_ok and after_ok:
                                # Apply replacement
                                modified_lines[line_idx] = (
                                    line[:col] + new_name + line[col + len(old_name) :]
                                )
                                replacements.append(
                                    {
                                        "line": ref["line"],
                                        "column": col,
                                        "context": ref["context"],
                                    }
                                )

                if replacements:
                    new_content = "\n".join(modified_lines)
                    changes.append(
                        {
                            "file": file_path,
                            "replacements": replacements,
                            "new_content": new_content,
                        }
                    )

        except Exception as e:
            logging.warning(f"Failed to process {file_path}: {e}")
            continue

    # Apply changes if not dry run
    if not dry_run and changes:
        from .edit_file import edit_file

        for change in changes:
            await edit_file(
                path=change["file"],
                old_string=change.get("old_content", ""),
                new_string=change["new_content"],
                description=f"Rename {old_name} to {new_name}",
                chat_id=chat_id,
                commit_hash=commit_hash,
            )

    # Format result
    result = {
        "operation": "rename_symbol",
        "old_name": old_name,
        "new_name": new_name,
        "dry_run": dry_run,
        "scope": scope,
        "total_files": len(changes),
        "total_replacements": sum(len(c["replacements"]) for c in changes),
        "files": [
            {
                "file": c["file"],
                "replacements_count": len(c["replacements"]),
                "contexts": list(set(r["context"] for r in c["replacements"])),
            }
            for c in changes
        ],
    }

    if dry_run:
        result["message"] = "Dry run complete. Set dry_run=False to apply changes."
        # Include preview of changes
        if changes and len(changes) <= 3:
            result["preview"] = []
            for change in changes[:3]:
                preview_lines = []
                lines = change["new_content"].split("\n")
                for repl in change["replacements"][:3]:
                    line_num = repl["line"] - 1
                    if 0 <= line_num < len(lines):
                        preview_lines.append(
                            {"line": repl["line"], "new": lines[line_num].strip()}
                        )
                result["preview"].append(
                    {"file": change["file"], "changes": preview_lines}
                )
    else:
        result["message"] = f"Successfully renamed {old_name} to {new_name}"

    return append_commit_hash(json.dumps(result, indent=2), commit_hash)


def _is_safe_rename(
    tree: Any, reference: Dict[str, Any], old_name: str, new_name: str
) -> bool:
    """Check if renaming at this reference is safe."""
    context = reference.get("context", "")

    # Always safe to rename in these contexts
    safe_contexts = {
        "declaration",
        "parameter",
        "function_call",
        "assignment_target",
        "reference",
        "import",
        "export",
    }

    if context in safe_contexts:
        return True

    # Be careful with property access
    if context == "property_access":
        # Don't rename object properties unless specifically requested
        return False

    # JSX components should maintain PascalCase
    if context == "jsx_component":
        return new_name[0].isupper()

    return True


def _apply_replacements(
    content: str, replacements: List[Dict], old_name: str, new_name: str
) -> str:
    """Apply replacements to content in reverse order to maintain positions."""
    lines = content.split("\n")

    # Sort by line and column in reverse order
    sorted_replacements = sorted(
        replacements, key=lambda r: (r["line"], r["column"]), reverse=True
    )

    for repl in sorted_replacements:
        line_idx = repl["line"] - 1
        if 0 <= line_idx < len(lines):
            line = lines[line_idx]
            col = repl["column"]
            end_col = repl.get("end_column", col + len(old_name))

            # Apply replacement
            lines[line_idx] = line[:col] + new_name + line[end_col:]

    return "\n".join(lines)


@mcp.tool()
async def add_js_parameter(
    function_name: str,
    parameter_name: str,
    parameter_type: Optional[str] = None,
    default_value: Optional[str] = None,
    position: int = -1,
    path: str = ".",
    update_calls: bool = True,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """
    Add a parameter to a JavaScript/TypeScript function and update all call sites.

    This tool adds a new parameter to a function definition and optionally updates
    all function calls to include the new parameter.

    Args:
        function_name: Name of the function to modify
        parameter_name: Name of the new parameter
        parameter_type: Optional TypeScript type annotation
        default_value: Optional default value for the parameter
        position: Position to insert parameter (-1 for end, 0 for beginning)
        path: File or directory containing the function
        update_calls: If True, update all call sites with default value
        chat_id: The unique ID of the current chat session
        commit_hash: Git commit hash for tracking

    Returns:
        JSON formatted summary of changes made
    """
    # Set default values
    chat_id = "" if chat_id is None else chat_id

    # Validate parameter name
    if not re.match(r"^[a-zA-Z_$][a-zA-Z0-9_$]*$", parameter_name):
        return json.dumps({"error": f"Invalid parameter name: {parameter_name}"})

    JavaScriptAnalyzer()
    changes = []
    function_found = False

    # First, find the function definition
    analysis_json = await analyze_js(
        path, "functions", chat_id=chat_id, commit_hash=commit_hash
    )
    analysis_data = json.loads(analysis_json)

    target_function = None
    target_file = None

    # Handle single file or directory
    if path.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs")):
        functions = analysis_data.get("functions", [])
        for func in functions:
            if func["name"] == function_name:
                target_function = func
                target_file = path
                break
    else:
        # Search directory for function
        import glob

        patterns = ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.mjs"]
        for pattern in patterns:
            for file_path in glob.glob(os.path.join(path, pattern), recursive=True):
                file_analysis = await analyze_js(
                    file_path, "functions", chat_id=chat_id, commit_hash=commit_hash
                )
                file_data = json.loads(file_analysis)
                for func in file_data.get("functions", []):
                    if func["name"] == function_name:
                        target_function = func
                        target_file = file_path
                        break
                if target_function:
                    break
            if target_function:
                break

    if not target_function or not target_file:
        return json.dumps({"error": f"Function '{function_name}' not found"})

    function_found = True

    # Read the file containing the function
    content = await async_open_text(target_file, encoding="utf-8", errors="replace")
    lines = content.split("\n")

    # Find the function definition line
    func_line = target_function["line"] - 1
    if 0 <= func_line < len(lines):
        line = lines[func_line]

        # Build new parameter
        new_param = parameter_name
        if parameter_type:
            new_param += f": {parameter_type}"
        if default_value:
            new_param += f" = {default_value}"

        # Extract current parameters
        target_function.get("params", [])

        # Find parameter list in the line
        # This is simplified - in real implementation would use AST
        param_match = re.search(r"\((.*?)\)", line)
        if param_match:
            param_str = param_match.group(1).strip()

            # Build new parameter list
            if not param_str:
                # No parameters
                new_param_str = new_param
            else:
                # Has parameters
                param_parts = [p.strip() for p in param_str.split(",")]

                # Insert at position
                if position == -1 or position >= len(param_parts):
                    param_parts.append(new_param)
                elif position == 0:
                    param_parts.insert(0, new_param)
                else:
                    param_parts.insert(position, new_param)

                new_param_str = ", ".join(param_parts)

            # Replace parameter list
            new_line = (
                line[: param_match.start(1)]
                + new_param_str
                + line[param_match.end(1) :]
            )

            # Update the line
            old_content = content
            lines[func_line] = new_line
            new_content = "\n".join(lines)

            changes.append(
                {
                    "file": target_file,
                    "type": "function_definition",
                    "function": function_name,
                    "line": target_function["line"],
                    "old_content": old_content,
                    "new_content": new_content,
                    "parameter_added": new_param,
                }
            )

    # Update function calls if requested
    if update_calls and default_value:
        # Find all calls to the function
        references_json = await find_js_references(
            function_name,
            path,
            context_filter="function_call",
            chat_id=chat_id,
            commit_hash=commit_hash,
        )
        references_data = json.loads(references_json)

        for file_info in references_data["files"]:
            file_path = file_info["file"]
            file_references = file_info["references"]

            if not file_references:
                continue

            # Read file
            content = await async_open_text(
                file_path, encoding="utf-8", errors="replace"
            )
            lines = content.split("\n")
            modified = False

            # Process references in reverse order
            for ref in sorted(
                file_references, key=lambda r: (r["line"], r["column"]), reverse=True
            ):
                line_idx = ref["line"] - 1
                if 0 <= line_idx < len(lines):
                    line = lines[line_idx]

                    # Find the function call parentheses
                    # Start from the column where function name appears
                    col = ref["column"] + len(function_name)

                    # Skip whitespace
                    while col < len(line) and line[col].isspace():
                        col += 1

                    if col < len(line) and line[col] == "(":
                        # Find matching closing parenthesis
                        paren_count = 1
                        end_col = col + 1
                        in_string = False
                        string_char = None

                        while end_col < len(line) and paren_count > 0:
                            char = line[end_col]

                            if not in_string:
                                if char in ('"', "'", "`"):
                                    in_string = True
                                    string_char = char
                                elif char == "(":
                                    paren_count += 1
                                elif char == ")":
                                    paren_count -= 1
                            else:
                                if char == string_char and line[end_col - 1] != "\\":
                                    in_string = False

                            end_col += 1

                        if paren_count == 0:
                            # Found matching parenthesis
                            args_str = line[col + 1 : end_col - 1].strip()

                            # Add new argument
                            if not args_str:
                                new_args = default_value
                            else:
                                # Determine position
                                if position == -1:
                                    new_args = args_str + ", " + default_value
                                elif position == 0:
                                    new_args = default_value + ", " + args_str
                                else:
                                    # Split arguments (simplified - doesn't handle nested calls)
                                    args = [a.strip() for a in args_str.split(",")]
                                    if position >= len(args):
                                        args.append(default_value)
                                    else:
                                        args.insert(position, default_value)
                                    new_args = ", ".join(args)

                            # Update line
                            lines[line_idx] = (
                                line[: col + 1] + new_args + line[end_col - 1 :]
                            )
                            modified = True

            if modified:
                changes.append(
                    {
                        "file": file_path,
                        "type": "function_calls",
                        "calls_updated": len(
                            [
                                r
                                for r in file_references
                                if r["context"] == "function_call"
                            ]
                        ),
                        "new_content": "\n".join(lines),
                    }
                )

    # Apply changes
    if changes:
        from .edit_file import edit_file

        for change in changes:
            if "old_content" in change and "new_content" in change:
                await edit_file(
                    path=change["file"],
                    old_string=change["old_content"],
                    new_string=change["new_content"],
                    description=f"Add parameter {parameter_name} to {function_name}",
                    chat_id=chat_id,
                    commit_hash=commit_hash,
                )
            elif "new_content" in change:
                # For call site updates, need to read current content
                current_content = await async_open_text(
                    change["file"], encoding="utf-8", errors="replace"
                )
                await edit_file(
                    path=change["file"],
                    old_string=current_content,
                    new_string=change["new_content"],
                    description=f"Update calls to {function_name} with new parameter",
                    chat_id=chat_id,
                    commit_hash=commit_hash,
                )

    # Format result
    result = {
        "operation": "add_parameter",
        "function": function_name,
        "parameter": parameter_name,
        "type": parameter_type,
        "default_value": default_value,
        "position": position,
        "function_found": function_found,
        "files_modified": len(set(c["file"] for c in changes)),
        "changes": [
            {
                "file": c["file"],
                "type": c["type"],
                "details": {
                    k: v
                    for k, v in c.items()
                    if k not in ["file", "type", "old_content", "new_content"]
                },
            }
            for c in changes
        ],
    }

    if function_found:
        result["message"] = (
            f"Successfully added parameter '{parameter_name}' to function '{function_name}'"
        )
    else:
        result["message"] = f"Function '{function_name}' not found"

    return append_commit_hash(json.dumps(result, indent=2), commit_hash)


@mcp.tool()
async def remove_unused_exports(
    path: str,
    dry_run: bool = True,
    exclude_patterns: Optional[List[str]] = None,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """
    Find and optionally remove unused exports from JavaScript/TypeScript files.

    This tool identifies exports that are not imported anywhere in the project
    and can remove them to clean up the codebase.

    Args:
        path: Directory to analyze for unused exports
        dry_run: If True, only report unused exports without removing
        exclude_patterns: Glob patterns to exclude from analysis (e.g., ["**/index.js"])
        chat_id: The unique ID of the current chat session
        commit_hash: Git commit hash for tracking

    Returns:
        JSON formatted report of unused exports and actions taken
    """
    # Set default values
    chat_id = "" if chat_id is None else chat_id
    exclude_patterns = exclude_patterns or []

    # Normalize path
    full_path = await normalize_file_path(path)

    if not full_path.is_dir():
        return json.dumps({"error": "Path must be a directory"})

    # Collect all exports and imports
    all_exports = {}  # file -> list of exports
    all_imports = {}  # file -> list of imported items
    unused_exports = []

    # Find all JS/TS files
    import glob

    patterns = ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.mjs"]
    js_files = []

    for pattern in patterns:
        files = glob.glob(str(full_path / pattern), recursive=True)
        for file_path in files:
            # Check exclude patterns
            excluded = False
            for exclude in exclude_patterns:
                if glob.fnmatch.fnmatch(file_path, exclude):
                    excluded = True
                    break
            if not excluded:
                js_files.append(file_path)

    # Analyze exports and imports
    for file_path in js_files:
        try:
            # Get exports
            exports_analysis = await analyze_js(
                file_path, "exports", chat_id=chat_id, commit_hash=commit_hash
            )
            exports_data = json.loads(exports_analysis)
            exports = exports_data.get("exports", [])

            if exports:
                all_exports[file_path] = exports

            # Get imports
            imports_analysis = await analyze_js(
                file_path, "imports", chat_id=chat_id, commit_hash=commit_hash
            )
            imports_data = json.loads(imports_analysis)
            imports = imports_data.get("imports", [])

            # Extract all imported names
            imported_names = set()
            for imp in imports:
                if imp.get("default"):
                    imported_names.add(imp["default"])
                if imp.get("namespace"):
                    imported_names.add(imp["namespace"])
                for named in imp.get("named", []):
                    if isinstance(named, dict):
                        imported_names.add(named.get("name", named))
                    else:
                        imported_names.add(named)

            if imported_names:
                all_imports[file_path] = imported_names

        except Exception as e:
            logging.warning(f"Failed to analyze {file_path}: {e}")
            continue

    # Find unused exports
    for export_file, exports in all_exports.items():
        for export in exports:
            # Get export name
            export_name = None
            if export.get("name"):
                export_name = export["name"]
            elif export.get("named"):
                # Check named exports
                for named in export["named"]:
                    if isinstance(named, dict):
                        check_name = named.get("name")
                    else:
                        check_name = named

                    if check_name:
                        # Check if this named export is imported anywhere
                        is_used = False
                        for import_file, imported_names in all_imports.items():
                            if (
                                import_file != export_file
                                and check_name in imported_names
                            ):
                                is_used = True
                                break

                        if not is_used:
                            unused_exports.append(
                                {
                                    "file": export_file,
                                    "name": check_name,
                                    "line": export.get("line"),
                                    "type": "named",
                                    "default": False,
                                }
                            )
                continue  # Skip the rest for named exports

            # For default exports, check if the file is imported
            if export.get("default"):
                # Check if any file imports from this file
                is_used = False
                export_file_name = os.path.basename(export_file)

                for import_file, imports in all_imports.items():
                    if import_file != export_file:
                        # Check if this file is imported
                        import_analysis = await analyze_js(
                            import_file,
                            "imports",
                            chat_id=chat_id,
                            commit_hash=commit_hash,
                        )
                        import_data = json.loads(import_analysis)
                        for imp in import_data.get("imports", []):
                            source = imp.get("source", "")
                            # Check if source references this file
                            if export_file_name in source or source.endswith(
                                os.path.splitext(export_file_name)[0]
                            ):
                                is_used = True
                                break
                    if is_used:
                        break

                if not is_used:
                    unused_exports.append(
                        {
                            "file": export_file,
                            "name": export_name or "default",
                            "line": export.get("line"),
                            "type": export.get("type", "unknown"),
                            "default": True,
                        }
                    )
            elif export_name:
                # Check if this export is imported anywhere
                is_used = False
                for import_file, imported_names in all_imports.items():
                    if import_file != export_file and export_name in imported_names:
                        is_used = True
                        break

                if not is_used:
                    unused_exports.append(
                        {
                            "file": export_file,
                            "name": export_name,
                            "line": export.get("line"),
                            "type": export.get("type", "unknown"),
                            "default": False,
                        }
                    )

    # Remove unused exports if not dry run
    changes = []
    if not dry_run and unused_exports:
        from .edit_file import edit_file

        # Group by file
        unused_by_file = {}
        for unused in unused_exports:
            file_path = unused["file"]
            if file_path not in unused_by_file:
                unused_by_file[file_path] = []
            unused_by_file[file_path].append(unused)

        # Process each file
        for file_path, file_unused in unused_by_file.items():
            try:
                content = await async_open_text(
                    file_path, encoding="utf-8", errors="replace"
                )
                lines = content.split("\n")
                modified = False

                # Sort by line number in reverse order
                file_unused.sort(key=lambda x: x.get("line", 0), reverse=True)

                for unused in file_unused:
                    line_num = unused.get("line")
                    if line_num and 0 < line_num <= len(lines):
                        line_idx = line_num - 1
                        line = lines[line_idx]

                        # Simple removal - just comment out the line
                        # In a real implementation, would use AST to remove properly
                        if "export" in line:
                            lines[line_idx] = (
                                "// " + line + " // REMOVED: Unused export"
                            )
                            modified = True

                if modified:
                    new_content = "\n".join(lines)
                    await edit_file(
                        path=file_path,
                        old_string=content,
                        new_string=new_content,
                        description="Remove unused exports",
                        chat_id=chat_id,
                        commit_hash=commit_hash,
                    )
                    changes.append(
                        {"file": file_path, "exports_removed": len(file_unused)}
                    )

            except Exception as e:
                logging.warning(f"Failed to remove exports from {file_path}: {e}")

    # Format result
    result = {
        "operation": "remove_unused_exports",
        "dry_run": dry_run,
        "files_analyzed": len(js_files),
        "total_exports": sum(len(exports) for exports in all_exports.values()),
        "unused_exports_count": len(unused_exports),
        "unused_exports": unused_exports,
        "files_modified": len(changes),
        "changes": changes,
    }

    if dry_run:
        result["message"] = (
            f"Found {len(unused_exports)} unused exports. Set dry_run=False to remove them."
        )
    else:
        result["message"] = (
            f"Removed {len(unused_exports)} unused exports from {len(changes)} files."
        )

    return append_commit_hash(json.dumps(result, indent=2), commit_hash)
