# JavaScript/TypeScript AST Analysis Tools

This document describes the new AST-based code analysis tools for JavaScript and TypeScript files in codemcp.

## Overview

The `analyze_js`, `find_js_references`, and refactoring tools provide semantic code understanding using Tree-sitter parsers, with automatic fallback to regex patterns when parsing fails.

## Supported File Types

- `.js` - JavaScript
- `.ts` - TypeScript
- `.jsx` - React JavaScript
- `.tsx` - React TypeScript
- `.mjs` - ES Modules

## Tools

### analyze_js

Analyzes JavaScript/TypeScript file structure using AST parsing.

**Parameters:**
- `path`: Path to the file to analyze
- `analysis_type`: Type of analysis to perform
  - `"summary"`: Overview of functions, imports, exports, classes
  - `"functions"`: Detailed function information with parameters
  - `"classes"`: Class declarations with inheritance
  - `"imports"`: Import statements with named/default/namespace imports
  - `"exports"`: Export statements with named/default exports
  - `"all"`: Complete analysis

**Example Usage:**
```python
# Get overview of a React component
analyze_js(path="components/Button.jsx", analysis_type="summary")

# Extract all functions with details
analyze_js(path="utils/helpers.ts", analysis_type="functions")

# Analyze imports and dependencies
analyze_js(path="index.js", analysis_type="imports")
```

**Example Output:**
```json
{
  "file": "components/Button.jsx",
  "summary": {
    "functions_count": 3,
    "classes_count": 0,
    "imports_count": 4,
    "exports_count": 1,
    "has_default_export": true,
    "main_exports": ["Button"]
  }
}
```

### find_js_references

Finds all references to a JavaScript/TypeScript symbol with semantic context.

**Parameters:**
- `symbol`: The symbol name to search for
- `path`: File or directory path to search in
- `context_filter`: Optional filter for reference context
  - `"function_call"`: Only function calls
  - `"declaration"`: Only declarations
  - `"import"`: Only imports
  - `"export"`: Only exports
  - `"jsx_component"`: Only JSX component usage
  - `"new_instance"`: Only new instantiations
  - `"property_access"`: Only property access
  - `"type_reference"`: Only type references (TypeScript)

**Example Usage:**
```python
# Find all references to a function
find_js_references(symbol="getUserData", path="src/")

# Find only function calls
find_js_references(symbol="fetchAPI", path="src/", context_filter="function_call")

# Find JSX component usage
find_js_references(symbol="Button", path="components/", context_filter="jsx_component")
```

**Example Output:**
```json
{
  "symbol": "getUserData",
  "files_analyzed": 15,
  "files_with_references": 4,
  "total_references": 8,
  "references_by_context": {
    "function_call": 5,
    "import": 2,
    "declaration": 1
  },
  "files": [
    {
      "file": "src/api/user.js",
      "references": [
        {
          "line": 42,
          "column": 12,
          "context": "declaration",
          "code": "export async function getUserData(userId) {",
          "scope": "global"
        }
      ]
    }
  ]
}
```

### rename_js_symbol

Safely rename a JavaScript/TypeScript symbol across all files using AST-based refactoring.

**Parameters:**
- `old_name`: Current name of the symbol
- `new_name`: New name for the symbol
- `path`: File or directory to refactor
- `dry_run`: If True, preview changes without modifying files
- `scope`: Optional scope to limit renaming (e.g., "function:processData")

**Example Usage:**
```python
# Preview renaming a function
rename_js_symbol(old_name="getUserData", new_name="fetchUserProfile", path="src/", dry_run=True)

# Actually rename the symbol
rename_js_symbol(old_name="getUserData", new_name="fetchUserProfile", path="src/", dry_run=False)

# Rename only within a specific scope
rename_js_symbol(old_name="data", new_name="userData", path="src/", scope="function:processUser")
```

**Example Output:**
```json
{
  "operation": "rename_symbol",
  "old_name": "getUserData",
  "new_name": "fetchUserProfile",
  "dry_run": false,
  "total_files": 5,
  "total_replacements": 12,
  "message": "Successfully renamed getUserData to fetchUserProfile",
  "files": [
    {
      "file": "src/api/user.js",
      "replacements_count": 1,
      "contexts": ["declaration"]
    },
    {
      "file": "src/components/Profile.js",
      "replacements_count": 3,
      "contexts": ["function_call", "import"]
    }
  ]
}
```

### add_js_parameter

Add a parameter to a JavaScript/TypeScript function and update all call sites.

**Parameters:**
- `function_name`: Name of the function to modify
- `parameter_name`: Name of the new parameter
- `parameter_type`: Optional TypeScript type annotation
- `default_value`: Optional default value for the parameter
- `position`: Position to insert parameter (-1 for end, 0 for beginning)
- `path`: File or directory containing the function
- `update_calls`: If True, update all call sites with default value

**Example Usage:**
```python
# Add a parameter with default value
add_js_parameter(
    function_name="processData",
    parameter_name="options",
    parameter_type="{ uppercase?: boolean }",
    default_value="{ uppercase: true }",
    position=-1,
    path="src/",
    update_calls=True
)

# Add parameter without updating calls
add_js_parameter(
    function_name="validate",
    parameter_name="strict",
    default_value="false",
    position=0,
    path="utils.js",
    update_calls=False
)
```

**Example Output:**
```json
{
  "operation": "add_parameter",
  "function": "processData",
  "parameter": "options",
  "type": "{ uppercase?: boolean }",
  "default_value": "{ uppercase: true }",
  "function_found": true,
  "files_modified": 4,
  "message": "Successfully added parameter 'options' to function 'processData'"
}
```

### remove_unused_exports

Find and optionally remove unused exports from JavaScript/TypeScript files.

**Parameters:**
- `path`: Directory to analyze for unused exports
- `dry_run`: If True, only report unused exports without removing
- `exclude_patterns`: Glob patterns to exclude from analysis (e.g., ["**/index.js"])

**Example Usage:**
```python
# Find unused exports (dry run)
remove_unused_exports(path="src/", dry_run=True)

# Remove unused exports
remove_unused_exports(path="src/", dry_run=False)

# Exclude certain files
remove_unused_exports(
    path="src/",
    dry_run=False,
    exclude_patterns=["**/index.js", "**/public-api.ts"]
)
```

**Example Output:**
```json
{
  "operation": "remove_unused_exports",
  "dry_run": false,
  "files_analyzed": 45,
  "total_exports": 120,
  "unused_exports_count": 23,
  "files_modified": 8,
  "message": "Removed 23 unused exports from 8 files",
  "unused_exports": [
    {
      "file": "src/utils/helpers.js",
      "name": "deprecatedHelper",
      "line": 45,
      "type": "function"
    }
  ]
}
```

## Features

### AST-Based Analysis
- Accurate parsing using Tree-sitter
- Understands JavaScript and TypeScript syntax
- Handles modern ES6+ features
- Supports JSX/TSX syntax

### Semantic Understanding
- Distinguishes between different usage contexts
- Tracks scope information
- Handles complex patterns like destructuring
- Understands TypeScript-specific features

### Safe Refactoring
- Preview changes before applying (dry run)
- Preserves code structure and formatting
- Handles edge cases (shadowing, property shorthand)
- Updates all references accurately

### Fallback Support
- Automatically falls back to regex patterns if parsing fails
- Handles malformed or incomplete code gracefully
- Always provides some results even with syntax errors

### Performance
- Fast Tree-sitter parsing
- Efficient file traversal
- Minimal memory overhead

## Use Cases

### Code Navigation
- Find where a function is defined
- Locate all calls to a specific API
- Track import/export relationships

### Refactoring
- Safely rename symbols across the codebase
- Add parameters to functions with automatic call site updates
- Remove unused exports to clean up code

### Code Analysis
- Count functions and classes
- Analyze module dependencies
- Extract API surface area
- Find dead code

### Documentation
- Generate function lists
- Extract method signatures
- Map component hierarchies

## Implementation Details

The tools are implemented in `codemcp/tools/analyze_js.py` and use:
- `tree-sitter` and `tree-sitter-languages` for parsing
- Existing smart_search patterns for fallback
- Async file operations for performance

## Installation

The Tree-sitter dependencies are automatically installed with:
```bash
uv pip install -e ".[dev]"
```

## Testing

Run the tests with:
```bash
# End-to-end tests
./run_test.sh e2e/test_analyze_js.py

# Unit tests
./run_test.sh tests/test_analyze_js.py
```

## Best Practices

1. **Always use dry run first** for refactoring operations to preview changes
2. **Backup your code** or ensure it's committed to version control
3. **Test after refactoring** to ensure functionality is preserved
4. **Use context filters** to narrow down symbol searches
5. **Exclude generated files** when removing unused exports
