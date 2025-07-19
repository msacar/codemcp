# Smart Search Guide for JavaScript/TypeScript

The smart search tools provide code-aware search capabilities specifically designed for JavaScript and TypeScript projects. Unlike regular grep, these tools understand code structure and can differentiate between definitions, usages, and imports.

## Available Tools

### 1. find_definition
Finds where a symbol is defined (classes, functions, variables, interfaces, types).

```python
# Examples:
find_definition("UserManager")  # Find class definition
find_definition("getUserById")  # Find function definition
find_definition("Props")        # Find interface/type definition
```

**What it finds:**
- ES6 classes: `class UserManager`, `export class UserManager`
- Functions: `function getData()`, `export async function getData()`
- Arrow functions: `const getData = () =>`, `export const getData = async () =>`
- TypeScript interfaces: `interface Props`, `export interface Props`
- Type aliases: `type UserType = {...}`, `export type UserType = ...`
- Enums: `enum Status`, `const enum Status`

### 2. find_usages
Finds where a symbol is used (function calls, instantiations, property access).

```python
# Examples:
find_usages("UserManager")      # Find where class is instantiated
find_usages("getData")          # Find function calls
find_usages("validateEmail")    # Find all calls to this function
```

**What it finds:**
- Function calls: `getData()`, `await getData()`
- Class instantiation: `new UserManager()`
- Property/method access: `.updateUser()`
- Type usage: `: UserType`, `<UserType>`

### 3. find_imports
Finds where a module or symbol is imported.

```python
# Examples:
find_imports("UserManager")     # Find files importing this class
find_imports("react")           # Find files importing React
find_imports("./utils")         # Find files importing from utils
```

**What it finds:**
- ES6 named imports: `import { UserManager } from './models'`
- Default imports: `import React from 'react'`
- Namespace imports: `import * as utils from './utils'`
- CommonJS: `const { UserManager } = require('./models')`
- Dynamic imports: `import('./lazy-module')`

## Key Features

1. **Fast Regex-Based**: Uses optimized regex patterns for speed
2. **JS/TS Aware**: Understands modern JavaScript and TypeScript syntax
3. **Context Display**: Shows surrounding code for better understanding
4. **Multiple Pattern Matching**: Tries various patterns to catch different coding styles
5. **File Filtering**: Works with .js, .jsx, .ts, .tsx, .mjs, .cjs files

## Usage Examples

### Finding a React Component
```bash
# Find where MyComponent is defined
find_definition MyComponent /path/to/project

# Find where it's used
find_usages MyComponent /path/to/project

# Find where it's imported
find_imports MyComponent /path/to/project
```

### Tracing a Function
```bash
# 1. Find where validateEmail is defined
find_definition validateEmail

# 2. Find all places it's called
find_usages validateEmail

# 3. Find which files import it
find_imports validateEmail
```

### Understanding a Class
```bash
# Find the UserManager class definition
find_definition UserManager

# Find all instantiations and usage
find_usages UserManager --exclude_definitions

# See the import pattern
find_imports UserManager
```

## Limitations

1. **Regex-based**: May have false positives/negatives in complex code
2. **No semantic understanding**: Can't resolve aliases or renamed imports
3. **No type inference**: Can't follow TypeScript type relationships
4. **Comments included**: May match symbols in comments (use context to verify)

## Tips for Best Results

1. Use specific symbol names (avoid generic names like "data" or "value")
2. Check the context shown in results to verify matches
3. Use file include patterns to narrow search scope
4. Combine with regular grep for comment/string searches

## Implementation Details

The smart search tools build on the existing git grep functionality but add:
- Pre-defined patterns for JS/TS syntax
- Line-by-line analysis for accurate results
- Context extraction for better understanding
- Type detection (class vs function vs variable)
- Duplicate removal and sorting

For the implementation code, see `/codemcp/tools/smart_search.py`.
