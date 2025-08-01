#!/usr/bin/env python3
"""Smart search tools for JavaScript/TypeScript code navigation."""

import logging
import os
import re
from typing import Dict, List, Optional

from ..async_file_utils import async_open_text
from ..mcp import mcp
from .commit_utils import append_commit_hash
from .grep import git_grep

__all__ = [
    "grep_find_definition",
    "grep_find_usages",
    "grep_find_imports",
    "JS_TS_PATTERNS",
]

# JavaScript/TypeScript specific patterns
JS_TS_PATTERNS = {
    # Class definitions - simplified for git grep
    "class": r"class[ ]+{symbol}",
    "export_class": r"export[ ]+class[ ]+{symbol}",
    "export_default_class": r"export[ ]+default[ ]+class[ ]+{symbol}",
    # Function definitions - avoid parentheses
    "function": r"function[ ]+{symbol}",
    "async_function": r"async[ ]+function[ ]+{symbol}",
    "export_function": r"export[ ]+function[ ]+{symbol}",
    # Arrow functions and const functions
    "const_function": r"const[ ]+{symbol}[ ]*=",
    "let_function": r"let[ ]+{symbol}[ ]*=",
    "var_function": r"var[ ]+{symbol}[ ]*=",
    "export_const": r"export[ ]+const[ ]+{symbol}[ ]*=",
    # Methods in classes or objects - very simplified
    "method": r"{symbol}.*:",
    # TypeScript specific
    "interface": r"interface[ ]+{symbol}",
    "export_interface": r"export[ ]+interface[ ]+{symbol}",
    "type_alias": r"type[ ]+{symbol}[ ]*=",
    "export_type": r"export[ ]+type[ ]+{symbol}[ ]*=",
    "enum": r"enum[ ]+{symbol}",
    "const_enum": r"const[ ]+enum[ ]+{symbol}",
    # React components (common patterns)
    "react_component": r"const[ ]+{symbol}[ ]*[:=].*React",
    "react_function_component": r"function[ ]+{symbol}.*return.*<",
}

# Patterns for finding usages (not definitions)
USAGE_PATTERNS = {
    "function_call": r"{symbol}[ ]*\(",  # Function calls
    "jsx_component": r"<{symbol}",  # JSX component usage
    "new_instance": r"new[ ]+{symbol}",
    "property_access": r"\.{symbol}",
    "import_named": r"import[ ]*\{{[^}}]*{symbol}[^}}]*\}}[ ]*from",  # Named imports only
    "import_default": r"import[ ]+{symbol}[ ]+from",
    "require": r"require[ ]*\([^)]*{symbol}[^)]*\)",
    "require_destructure": r"const[ ]*\{{[^}}]*{symbol}[^}}]*\}}[ ]*=[ ]*require",
    "type_usage": r":[ ]*{symbol}",
}


def escape_symbol_for_regex(symbol: str) -> str:
    """Escape special regex characters in symbol name."""
    return re.escape(symbol)


async def get_line_context(
    file_path: str, pattern: str, symbol: str, pattern_name: str = None
) -> List[Dict[str, any]]:
    """Get line numbers and context for matches in a file."""
    matches = []
    try:
        content = await async_open_text(file_path, encoding="utf-8", errors="replace")
        lines = content.split("\n")

        # Compile pattern with symbol
        regex_pattern = pattern.format(symbol=escape_symbol_for_regex(symbol))
        compiled_pattern = re.compile(regex_pattern, re.IGNORECASE)

        for line_num, line in enumerate(lines, 1):
            # Skip comment lines
            stripped_line = line.strip()
            if (
                stripped_line.startswith("//")
                or stripped_line.startswith("/*")
                or stripped_line.startswith("*")
            ):
                continue

            if compiled_pattern.search(line):
                # Special handling for function_call pattern - exclude definitions
                if pattern_name == "function_call" and "function " in line:
                    # Check if this is a function definition
                    if re.search(rf"function\s+{re.escape(symbol)}\s*\(", line):
                        continue

                # Get surrounding context (2 lines before and after)
                start = max(0, line_num - 3)
                end = min(len(lines), line_num + 2)
                context = lines[start:end]

                matches.append(
                    {
                        "file": file_path,
                        "line": line_num,
                        "text": line.strip(),
                        "context": "\n".join(context),
                        "type": _determine_definition_type(line, symbol),
                    }
                )
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")

    return matches


def _determine_definition_type(line: str, symbol: str) -> str:
    """Determine what type of definition this is."""
    line_lower = line.lower()

    if "class" in line_lower:
        return "class"
    elif "interface" in line_lower:
        return "interface"
    elif "type" in line_lower and "=" in line:
        return "type"
    elif "enum" in line_lower:
        return "enum"
    elif "function" in line_lower:
        return "function"
    elif "=>" in line:
        return "arrow_function"
    elif "const" in line_lower or "let" in line_lower or "var" in line_lower:
        return "variable"
    else:
        return "method"


@mcp.tool()
async def grep_find_definition(
    symbol: str,
    path: str = ".",
    include: str = "*.js,*.jsx,*.ts,*.tsx,*.mjs,*.cjs",
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Find where a JavaScript/TypeScript symbol is defined.

    This tool searches for class, function, interface, type, and variable definitions
    in JavaScript and TypeScript files using smart regex patterns.

    Args:
        symbol: The symbol name to find (e.g., "UserClass", "getData", "Props")
        path: The directory to search in (defaults to current directory)
        include: File patterns to include (defaults to JS/TS files)
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        A formatted string with the definition locations and context
    """
    try:
        all_matches = []
        files_to_check = set()

        # Try each definition pattern
        for pattern_name, pattern in JS_TS_PATTERNS.items():
            formatted_pattern = pattern.format(symbol=escape_symbol_for_regex(symbol))

            # Use git grep to find potential files
            try:
                logging.info(f"Trying pattern {pattern_name}: {formatted_pattern}")
                matched_files = await git_grep(formatted_pattern, path, include)
                logging.info(
                    f"Pattern {pattern_name} matched {len(matched_files)} files: {matched_files}"
                )
                files_to_check.update(matched_files)
            except Exception as e:
                logging.error(f"Pattern {pattern_name} failed with error: {e}")
                continue

        logging.info(f"Total files to check: {len(files_to_check)}")

        # Now get detailed information from each file
        for file_path in files_to_check:
            for pattern_name, pattern in JS_TS_PATTERNS.items():
                file_matches = await get_line_context(file_path, pattern, symbol)
                all_matches.extend(file_matches)

        # Remove duplicates (same file and line)
        unique_matches = []
        seen = set()
        for match in all_matches:
            key = (match["file"], match["line"])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        # Sort by file path and line number
        unique_matches.sort(key=lambda x: (x["file"], x["line"]))

        # Format results
        if not unique_matches:
            result = f"No definition found for '{symbol}' in {path}"
        else:
            result = f"Found {len(unique_matches)} definition(s) of '{symbol}':\n\n"

            for match in unique_matches:
                relative_path = os.path.relpath(match["file"], path)
                result += f"📍 {relative_path}:{match['line']} ({match['type']})\n"
                result += f"   {match['text']}\n\n"

                # Add brief context for better understanding
                if len(unique_matches) <= 3:  # Show context only for few matches
                    result += "   Context:\n"
                    for line in match["context"].split("\n"):
                        result += f"   | {line}\n"
                    result += "\n"

        # Append commit hash
        if path:
            result, _ = await append_commit_hash(result, path, commit_hash)

        return result

    except Exception as e:
        logging.error(f"Error in find_definition: {e}", exc_info=True)
        return f"Error finding definition: {e}"


@mcp.tool()
async def grep_find_usages(
    symbol: str,
    path: str = ".",
    include: str = "*.js,*.jsx,*.ts,*.tsx,*.mjs,*.cjs",
    exclude_definitions: bool = True,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Find where a JavaScript/TypeScript symbol is used (not defined).

    This tool searches for function calls, class instantiations, imports,
    and other usages of a symbol in JavaScript and TypeScript files.

    Args:
        symbol: The symbol name to find usages of
        path: The directory to search in (defaults to current directory)
        include: File patterns to include (defaults to JS/TS files)
        exclude_definitions: Whether to exclude definition locations (default: True)
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        A formatted string with the usage locations and context
    """
    try:
        all_matches = []
        files_to_check = set()

        # Get definition files to exclude if requested
        definition_files = set()
        if exclude_definitions:
            for pattern_name, pattern in JS_TS_PATTERNS.items():
                formatted_pattern = pattern.format(
                    symbol=escape_symbol_for_regex(symbol)
                )
                try:
                    def_files = await git_grep(formatted_pattern, path, include)
                    definition_files.update(def_files)
                except Exception:
                    continue

        # Find usages
        for pattern_name, pattern in USAGE_PATTERNS.items():
            formatted_pattern = pattern.format(symbol=escape_symbol_for_regex(symbol))

            try:
                matched_files = await git_grep(formatted_pattern, path, include)
                files_to_check.update(matched_files)
            except Exception as e:
                logging.debug(f"Usage pattern {pattern_name} failed: {e}")
                continue

        # Get detailed information from each file
        for file_path in files_to_check:
            # Skip definition files if requested
            if exclude_definitions and file_path in definition_files:
                continue

            for pattern_name, pattern in USAGE_PATTERNS.items():
                file_matches = await get_line_context(
                    file_path, pattern, symbol, pattern_name
                )
                for match in file_matches:
                    match["usage_type"] = pattern_name
                all_matches.extend(file_matches)

        # Remove duplicates
        unique_matches = []
        seen = set()
        for match in all_matches:
            key = (match["file"], match["line"])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        # Sort by file path and line number
        unique_matches.sort(key=lambda x: (x["file"], x["line"]))

        # Format results
        if not unique_matches:
            result = f"No usages found for '{symbol}' in {path}"
        else:
            result = f"Found {len(unique_matches)} usage(s) of '{symbol}':\n\n"

            # Group by file for better readability
            current_file = None
            for match in unique_matches:
                relative_path = os.path.relpath(match["file"], path)

                if current_file != relative_path:
                    current_file = relative_path
                    result += f"\n📄 {relative_path}:\n"

                usage_type = match.get("usage_type", "usage").replace("_", " ")
                result += f"  Line {match['line']}: {usage_type}\n"
                result += f"    {match['text']}\n"

        # Append commit hash
        if path:
            result, _ = await append_commit_hash(result, path, commit_hash)

        return result

    except Exception as e:
        logging.error(f"Error in find_usages: {e}", exc_info=True)
        return f"Error finding usages: {e}"


@mcp.tool()
async def grep_find_imports(
    module_or_symbol: str,
    path: str = ".",
    include: str = "*.js,*.jsx,*.ts,*.tsx,*.mjs,*.cjs",
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Find where a module or symbol is imported in JavaScript/TypeScript files.

    This tool searches for import statements (ES6 imports and CommonJS require).

    Args:
        module_or_symbol: The module name or symbol to find imports of
        path: The directory to search in (defaults to current directory)
        include: File patterns to include (defaults to JS/TS files)
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        A formatted string with the import locations and types
    """
    try:
        import_patterns = {
            "es6_named": r"import.*{symbol}.*from",
            "es6_default": r"import[ ]+{symbol}[ ]+from",
            "es6_namespace": r"import[ ]*\*[ ]*as[ ]+{symbol}[ ]+from",
            "require_const": r"const[ ]+{symbol}[ ]*=[ ]*require",
            "require_destructure": r"const.*{symbol}.*=.*require",
            "dynamic_import": r"import.*{symbol}",
            "from_module": r"from.*{symbol}",
        }

        all_matches = []
        files_to_check = set()

        # Search for import patterns
        for pattern_name, pattern in import_patterns.items():
            formatted_pattern = pattern.format(
                symbol=escape_symbol_for_regex(module_or_symbol)
            )

            try:
                matched_files = await git_grep(formatted_pattern, path, include)
                files_to_check.update(matched_files)
            except Exception as e:
                logging.debug(f"Import pattern {pattern_name} failed: {e}")
                continue

        # Get detailed information
        for file_path in files_to_check:
            for pattern_name, pattern in import_patterns.items():
                file_matches = await get_line_context(
                    file_path, pattern, module_or_symbol
                )
                for match in file_matches:
                    match["import_type"] = pattern_name
                all_matches.extend(file_matches)

        # Remove duplicates
        unique_matches = []
        seen = set()
        for match in all_matches:
            key = (match["file"], match["line"])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        # Sort by file path and line number
        unique_matches.sort(key=lambda x: (x["file"], x["line"]))

        # Format results
        if not unique_matches:
            result = f"No imports found for '{module_or_symbol}' in {path}"
        else:
            result = (
                f"Found {len(unique_matches)} import(s) of '{module_or_symbol}':\n\n"
            )

            for match in unique_matches:
                relative_path = os.path.relpath(match["file"], path)
                import_type = match.get("import_type", "import").replace("_", " ")

                result += f"📦 {relative_path}:{match['line']} ({import_type})\n"
                result += f"   {match['text']}\n\n"

        # Append commit hash
        if path:
            result, _ = await append_commit_hash(result, path, commit_hash)

        return result

    except Exception as e:
        logging.error(f"Error in find_imports: {e}", exc_info=True)
        return f"Error finding imports: {e}"
