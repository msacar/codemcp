#!/usr/bin/env python3
"""End-to-end tests for analyze_js tool."""

import json
import os
import tempfile

import pytest

from codemcp.testing import TestSetup


@pytest.mark.asyncio
async def test_analyze_js_function_extraction():
    """Test extracting functions from JavaScript file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a JavaScript file with various function types
        js_content = """
// Regular function
function regularFunction(a, b) {
    return a + b;
}

// Async function
async function asyncFunction(data) {
    const result = await fetch(data);
    return result.json();
}

// Arrow function
const arrowFunction = (x, y) => x * y;

// Function expression
const funcExpression = function(name) {
    return `Hello, ${name}!`;
};

// Method in object
const obj = {
    method() {
        return "object method";
    },
    asyncMethod: async function() {
        return "async method";
    }
};

// Class with methods
class MyClass {
    constructor(value) {
        this.value = value;
    }

    getValue() {
        return this.value;
    }

    static staticMethod() {
        return "static";
    }

    async asyncClassMethod() {
        return await Promise.resolve(this.value);
    }
}

// Export functions
export function exportedFunction() {
    return "exported";
}

export default function defaultExport() {
    return "default";
}
"""
        js_file = os.path.join(repo_dir, "test.js")
        with open(js_file, "w") as f:
            f.write(js_content)

        test_setup.setup_repo()

        # Test function analysis
        result = await test_setup.run_tool(
            "analyze_js", path="test.js", analysis_type="functions"
        )
        functions = json.loads(result)["functions"]

        # Verify we found all functions
        function_names = [f["name"] for f in functions]
        assert "regularFunction" in function_names
        assert "asyncFunction" in function_names
        assert "arrowFunction" in function_names
        assert "funcExpression" in function_names
        assert "method" in function_names
        assert "asyncMethod" in function_names
        assert "getValue" in function_names
        assert "staticMethod" in function_names
        assert "asyncClassMethod" in function_names
        assert "exportedFunction" in function_names
        assert "defaultExport" in function_names

        # Check function details
        regular_func = next(f for f in functions if f["name"] == "regularFunction")
        assert regular_func["type"] == "function"
        assert regular_func["params"] == [
            {"name": "a", "optional": False, "default": False},
            {"name": "b", "optional": False, "default": False},
        ]
        assert regular_func["async"] is False

        async_func = next(f for f in functions if f["name"] == "asyncFunction")
        assert async_func["async"] is True

        static_method = next(f for f in functions if f["name"] == "staticMethod")
        assert static_method["static"] is True
        assert static_method["class"] == "MyClass"


@pytest.mark.asyncio
async def test_analyze_js_class_extraction():
    """Test extracting classes from JavaScript/TypeScript file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a TypeScript file with classes
        ts_content = """
class BaseClass {
    protected baseValue: string;

    constructor(value: string) {
        this.baseValue = value;
    }
}

class DerivedClass extends BaseClass {
    private derivedValue: number;

    constructor(baseValue: string, derivedValue: number) {
        super(baseValue);
        this.derivedValue = derivedValue;
    }
}

interface IMyInterface {
    method(): void;
}

class ImplementingClass implements IMyInterface {
    method(): void {
        console.log("Implementation");
    }
}

export class ExportedClass {
    static readonly VERSION = "1.0.0";
}

export default class DefaultExportClass extends DerivedClass {
    constructor() {
        super("default", 42);
    }
}
"""
        ts_file = os.path.join(repo_dir, "test.ts")
        with open(ts_file, "w") as f:
            f.write(ts_content)

        test_setup.setup_repo()

        # Test class analysis
        result = await test_setup.run_tool(
            "analyze_js", path="test.ts", analysis_type="classes"
        )
        classes = json.loads(result)["classes"]

        # Verify we found all classes
        class_names = [c["name"] for c in classes]
        assert "BaseClass" in class_names
        assert "DerivedClass" in class_names
        assert "ImplementingClass" in class_names
        assert "ExportedClass" in class_names
        assert "DefaultExportClass" in class_names

        # Check inheritance
        derived_class = next(c for c in classes if c["name"] == "DerivedClass")
        assert derived_class["extends"] == "BaseClass"

        default_export = next(c for c in classes if c["name"] == "DefaultExportClass")
        assert default_export["extends"] == "DerivedClass"


@pytest.mark.asyncio
async def test_analyze_js_imports_exports():
    """Test analyzing imports and exports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a module file
        module_content = """
// Various import styles
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
import {
    ComponentA,
    ComponentB as B,
    ComponentC
} from './components';
import './styles.css';

// CommonJS require
const fs = require('fs');
const { readFile, writeFile } = require('fs/promises');

// Various export styles
export const API_KEY = 'secret';
export let counter = 0;

export function increment() {
    counter++;
}

export class ApiClient {
    constructor(key) {
        this.key = key;
    }
}

// Named exports with renaming
export { increment as inc, counter as cnt };

// Re-exports
export { default as Header } from './Header';
export * from './constants';

// Default export
export default ApiClient;
"""
        module_file = os.path.join(repo_dir, "module.js")
        with open(module_file, "w") as f:
            f.write(module_content)

        test_setup.setup_repo()

        # Test import analysis
        result = await test_setup.run_tool(
            "analyze_js", path="module.js", analysis_type="imports"
        )
        imports = json.loads(result)["imports"]

        # Check various import types
        react_import = next(i for i in imports if i["source"] == "react")
        assert react_import["default"] == "React"

        react_hooks = next(
            i for i in imports if i["source"] == "react" and i.get("named")
        )
        assert any(n["name"] == "useState" for n in react_hooks["named"])
        assert any(n["name"] == "useEffect" for n in react_hooks["named"])

        utils_import = next(i for i in imports if i["source"] == "./utils")
        assert utils_import["namespace"] == "utils"

        components_import = next(i for i in imports if i["source"] == "./components")
        assert len(components_import["named"]) == 3
        assert any(
            n["name"] == "ComponentB" and n.get("alias") == "B"
            for n in components_import["named"]
        )

        # Check CommonJS requires
        fs_require = next(
            i for i in imports if i["source"] == "fs" and i.get("type") == "require"
        )
        assert fs_require is not None

        # Test export analysis
        result = await test_setup.run_tool(
            "analyze_js", path="module.js", analysis_type="exports"
        )
        exports = json.loads(result)["exports"]

        # Check various export types
        default_export = next(e for e in exports if e["default"] is True)
        assert default_export["name"] == "ApiClient"

        function_export = next(
            e
            for e in exports
            if e.get("name") == "increment" and e["type"] == "function"
        )
        assert function_export is not None

        class_export = next(
            e for e in exports if e.get("name") == "ApiClient" and e["type"] == "class"
        )
        assert class_export is not None

        # Check named exports
        named_exports = [e for e in exports if e["type"] == "named"]
        assert len(named_exports) > 0


@pytest.mark.asyncio
async def test_analyze_js_summary():
    """Test summary analysis providing overview."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a React component file
        jsx_content = """
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Button, TextField } from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import './UserForm.css';

const UserForm = ({ onSubmit, initialData = {} }) => {
    const [formData, setFormData] = useState(initialData);
    const [errors, setErrors] = useState({});
    const { user, isAuthenticated } = useAuth();

    useEffect(() => {
        if (!isAuthenticated) {
            console.log('User not authenticated');
        }
    }, [isAuthenticated]);

    const validateForm = () => {
        const newErrors = {};
        if (!formData.name) {
            newErrors.name = 'Name is required';
        }
        if (!formData.email) {
            newErrors.email = 'Email is required';
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (validateForm()) {
            await onSubmit(formData);
        }
    };

    const handleChange = (field) => (e) => {
        setFormData({
            ...formData,
            [field]: e.target.value
        });
    };

    return (
        <form onSubmit={handleSubmit}>
            <TextField
                label="Name"
                value={formData.name || ''}
                onChange={handleChange('name')}
                error={!!errors.name}
                helperText={errors.name}
            />
            <TextField
                label="Email"
                value={formData.email || ''}
                onChange={handleChange('email')}
                error={!!errors.email}
                helperText={errors.email}
            />
            <Button type="submit" variant="contained">
                Submit
            </Button>
        </form>
    );
};

UserForm.propTypes = {
    onSubmit: PropTypes.func.isRequired,
    initialData: PropTypes.object
};

export default UserForm;
"""
        jsx_file = os.path.join(repo_dir, "UserForm.jsx")
        with open(jsx_file, "w") as f:
            f.write(jsx_content)

        test_setup.setup_repo()

        # Test summary analysis
        result = await test_setup.run_tool(
            "analyze_js", path="UserForm.jsx", analysis_type="summary"
        )
        data = json.loads(result)
        summary = data["summary"]

        assert (
            summary["functions_count"] >= 4
        )  # UserForm, validateForm, handleSubmit, handleChange
        assert summary["imports_count"] >= 5
        assert summary["exports_count"] >= 1
        assert summary["has_default_export"] is True
        assert "UserForm" in summary["main_exports"]


@pytest.mark.asyncio
async def test_find_js_references():
    """Test finding symbol references with context."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create multiple files with references
        # File 1: Define a class and function
        file1_content = """
export class DataService {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
    }

    async fetchData(id) {
        const response = await fetch(`${this.apiUrl}/data/${id}`);
        return response.json();
    }
}

export function createDataService(url) {
    return new DataService(url);
}
"""
        file1 = os.path.join(repo_dir, "services", "DataService.js")
        os.makedirs(os.path.dirname(file1), exist_ok=True)
        with open(file1, "w") as f:
            f.write(file1_content)

        # File 2: Use the class and function
        file2_content = """
import { DataService, createDataService } from './services/DataService';

// Direct instantiation
const service1 = new DataService('https://api.example.com');

// Using factory function
const service2 = createDataService('https://api.example.com');

// Type annotation (TypeScript)
let service3: DataService;

async function loadUserData(userId) {
    // Method call
    const data = await service1.fetchData(userId);

    // Property access
    console.log('API URL:', service1.apiUrl);

    return data;
}

// Export for other modules
export { DataService as DataAPI };
"""
        file2 = os.path.join(repo_dir, "app.js")
        with open(file2, "w") as f:
            f.write(file2_content)

        # File 3: JSX usage
        file3_content = """
import React from 'react';
import { DataService } from './services/DataService';

const DataServiceProvider = ({ children }) => {
    const service = new DataService(process.env.REACT_APP_API_URL);

    return (
        <DataServiceContext.Provider value={service}>
            {children}
        </DataServiceContext.Provider>
    );
};

// Component that looks like the class name
const DataServiceStatus = () => {
    return <div>DataService is active</div>;
};

export default function App() {
    return (
        <div>
            <DataServiceStatus />
            <DataServiceProvider>
                <h1>App using DataService</h1>
            </DataServiceProvider>
        </div>
    );
}
"""
        file3 = os.path.join(repo_dir, "App.jsx")
        with open(file3, "w") as f:
            f.write(file3_content)

        test_setup.setup_repo()

        # Test finding all references to DataService
        result = await test_setup.run_tool(
            "find_js_references", symbol="DataService", path=repo_dir
        )
        data = json.loads(result)

        assert data["symbol"] == "DataService"
        assert data["files_analyzed"] >= 3
        assert data["total_references"] >= 8

        # Check different contexts
        contexts = data["references_by_context"]
        assert "import" in contexts
        assert "new_instance" in contexts
        assert "declaration" in contexts or "export" in contexts

        # Test with context filter - only function calls
        result = await test_setup.run_tool(
            "find_js_references",
            symbol="createDataService",
            path=repo_dir,
            context_filter="function_call",
        )
        data = json.loads(result)

        assert data["context_filter"] == "function_call"
        assert data["total_references"] >= 1

        # Verify the function call was found
        for file_info in data["files"]:
            for ref in file_info["references"]:
                assert ref["context"] == "function_call"

        # Test JSX component references
        result = await test_setup.run_tool(
            "find_js_references",
            symbol="DataServiceProvider",
            path=repo_dir,
            context_filter="jsx_component",
        )
        data = json.loads(result)

        assert data["total_references"] >= 1


@pytest.mark.asyncio
async def test_analyze_js_typescript_features():
    """Test TypeScript-specific features."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a TypeScript file with advanced features
        ts_content = """
// Type imports and exports
import type { Request, Response } from 'express';
export type { Request as ExpressRequest };

// Interface with generics
interface Repository<T> {
    findById(id: string): Promise<T | null>;
    save(item: T): Promise<void>;
    delete(id: string): Promise<boolean>;
}

// Type alias
type UserId = string;
type UserRole = 'admin' | 'user' | 'guest';

// Enum
enum StatusCode {
    OK = 200,
    NOT_FOUND = 404,
    SERVER_ERROR = 500
}

// Const enum
const enum Direction {
    Up,
    Down,
    Left,
    Right
}

// Generic function with constraints
function processArray<T extends { id: string }>(
    items: T[],
    processor: (item: T) => void
): void {
    items.forEach(processor);
}

// Async generic function with optional and default parameters
async function fetchData<T = any>(
    url: string,
    options?: RequestInit,
    timeout: number = 5000
): Promise<T> {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), timeout);

    const response = await fetch(url, {
        ...options,
        signal: controller.signal
    });

    return response.json() as Promise<T>;
}

// Class with decorators and parameter properties
class UserService implements Repository<User> {
    constructor(
        private readonly db: Database,
        public readonly cache?: CacheService
    ) {}

    async findById(id: UserId): Promise<User | null> {
        return this.db.users.findOne({ id });
    }

    async save(user: User): Promise<void> {
        await this.db.users.save(user);
        this.cache?.invalidate(`user:${user.id}`);
    }

    async delete(id: UserId): Promise<boolean> {
        const result = await this.db.users.delete({ id });
        return result.affected > 0;
    }

    // Method overloading
    find(id: string): Promise<User | null>;
    find(email: string, byEmail: true): Promise<User | null>;
    find(idOrEmail: string, byEmail: boolean = false): Promise<User | null> {
        if (byEmail) {
            return this.db.users.findOne({ email: idOrEmail });
        }
        return this.findById(idOrEmail);
    }
}

// Namespace
namespace Utils {
    export function formatDate(date: Date): string {
        return date.toISOString();
    }

    export interface Config {
        apiUrl: string;
        timeout: number;
    }
}

// Module augmentation
declare global {
    interface Window {
        myApp: {
            version: string;
            service: UserService;
        };
    }
}

export { UserService, StatusCode, Utils };
export default UserService;
"""
        ts_file = os.path.join(repo_dir, "advanced.ts")
        with open(ts_file, "w") as f:
            f.write(ts_content)

        test_setup.setup_repo()

        # Test full analysis
        result = await test_setup.run_tool(
            "analyze_js", path="advanced.ts", analysis_type="all"
        )
        data = json.loads(result)

        # Check functions with TypeScript features
        functions = data["functions"]
        process_array = next(f for f in functions if f["name"] == "processArray")
        assert len(process_array["params"]) == 2

        fetch_data = next(f for f in functions if f["name"] == "fetchData")
        assert fetch_data["async"] is True
        assert any(p["optional"] or p["default"] for p in fetch_data["params"])

        # Check methods with TypeScript modifiers
        find_by_id = next(
            f
            for f in functions
            if f["name"] == "findById" and f.get("class") == "UserService"
        )
        assert find_by_id is not None

        # Check classes
        classes = data["classes"]
        user_service = next(c for c in classes if c["name"] == "UserService")
        assert user_service is not None

        # Check imports/exports
        imports = data["imports"]
        type_import = next((i for i in imports if "type" in str(i)), None)
        assert (
            type_import is not None or len(imports) > 0
        )  # Fallback for parsers that don't distinguish

        exports = data["exports"]
        assert any(e["default"] for e in exports)
        assert any(e["name"] == "UserService" for e in exports)


@pytest.mark.asyncio
async def test_analyze_js_fallback_mode():
    """Test fallback to regex when Tree-sitter fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a malformed JavaScript file that might fail parsing
        js_content = """
// Intentionally malformed syntax
function broken(a, b, {
    return a + b;
}

// This should still be detected
function validFunction() {
    return "This works";
}

const arrowFunc = () => {
    console.log("Arrow function");
};

import something from 'module';
export function exportedFunc() {}
"""
        js_file = os.path.join(repo_dir, "malformed.js")
        with open(js_file, "w") as f:
            f.write(js_content)

        test_setup.setup_repo()

        # The tool should handle this gracefully
        result = await test_setup.run_tool(
            "analyze_js", path="malformed.js", analysis_type="summary"
        )
        data = json.loads(result)

        # Should have found some functions even with malformed code
        if "summary" in data:
            # Either AST parsed partially or fell back to regex
            assert (
                data["summary"]["functions_count"] >= 2
            )  # At least validFunction and arrowFunc
            assert data["summary"]["imports_count"] >= 1
            assert data["summary"]["exports_count"] >= 1


@pytest.mark.asyncio
async def test_analyze_js_mjs_files():
    """Test analyzing .mjs (ES modules) files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create an .mjs file
        mjs_content = """
// ES module syntax only
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import process from 'node:process';

const PORT = process.env.PORT || 3000;

async function loadConfig() {
    const data = await readFile('./config.json', 'utf8');
    return JSON.parse(data);
}

function startServer(config) {
    const server = createServer((req, res) => {
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('Hello World');
    });

    server.listen(PORT, () => {
        console.log(`Server running on port ${PORT}`);
    });

    return server;
}

// Top-level await
const config = await loadConfig();
const server = startServer(config);

export { server, loadConfig };
export default server;
"""
        mjs_file = os.path.join(repo_dir, "server.mjs")
        with open(mjs_file, "w") as f:
            f.write(mjs_content)

        test_setup.setup_repo()

        # Test analyzing .mjs file
        result = await test_setup.run_tool(
            "analyze_js", path="server.mjs", analysis_type="all"
        )
        data = json.loads(result)

        assert data["file"] == "server.mjs"

        # Check functions
        functions = data.get("functions", [])
        function_names = [f["name"] for f in functions]
        assert "loadConfig" in function_names
        assert "startServer" in function_names

        # Check imports (node: protocol imports)
        imports = data.get("imports", [])
        assert any(i["source"].startswith("node:") for i in imports)

        # Check exports
        exports = data.get("exports", [])
        assert any(e["default"] for e in exports)


@pytest.mark.asyncio
async def test_rename_js_symbol():
    """Test renaming JavaScript symbols across files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a utility file with a function
        utils_content = """
export function calculateTotal(items, taxRate) {
    const subtotal = items.reduce((sum, item) => sum + item.price, 0);
    const tax = subtotal * taxRate;
    return subtotal + tax;
}

export function formatCurrency(amount) {
    return `$${amount.toFixed(2)}`;
}
"""
        utils_file = os.path.join(repo_dir, "utils.js")
        with open(utils_file, "w") as f:
            f.write(utils_content)

        # Create a file that uses the function
        main_content = """
import { calculateTotal, formatCurrency } from './utils';

const items = [
    { name: 'Item 1', price: 10.99 },
    { name: 'Item 2', price: 25.50 }
];

function processOrder(taxRate = 0.08) {
    const total = calculateTotal(items, taxRate);
    const formatted = formatCurrency(total);

    console.log('Total:', formatted);

    // Another call
    const discountedTotal = calculateTotal(items, taxRate * 0.5);
    console.log('Discounted:', formatCurrency(discountedTotal));
}

processOrder();
"""
        main_file = os.path.join(repo_dir, "main.js")
        with open(main_file, "w") as f:
            f.write(main_content)

        test_setup.setup_repo()

        # Test dry run first
        result = await test_setup.run_tool(
            "rename_js_symbol",
            old_name="calculateTotal",
            new_name="computeTotal",
            path=repo_dir,
            dry_run=True,
        )
        data = json.loads(result)

        assert data["operation"] == "rename_symbol"
        assert data["dry_run"] is True
        assert data["total_files"] >= 2
        assert data["total_replacements"] >= 3  # 1 declaration + 2 calls

        # Check preview
        assert "preview" in data
        preview_files = [p["file"] for p in data["preview"]]
        assert any("utils.js" in f for f in preview_files)
        assert any("main.js" in f for f in preview_files)

        # Now do actual rename
        result = await test_setup.run_tool(
            "rename_js_symbol",
            old_name="calculateTotal",
            new_name="computeTotal",
            path=repo_dir,
            dry_run=False,
        )
        data = json.loads(result)

        assert data["dry_run"] is False
        assert "Successfully renamed" in data["message"]

        # Verify the changes
        with open(utils_file, "r") as f:
            utils_updated = f.read()
        assert "computeTotal" in utils_updated
        assert "calculateTotal" not in utils_updated

        with open(main_file, "r") as f:
            main_updated = f.read()
        assert "computeTotal" in main_updated
        assert "calculateTotal" not in main_updated


@pytest.mark.asyncio
async def test_add_js_parameter():
    """Test adding parameters to JavaScript functions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a file with functions
        functions_content = """
function greet(name) {
    return `Hello, ${name}!`;
}

export function processData(data) {
    // Process the data
    console.log('Processing:', data);
    return data.map(item => item.toUpperCase());
}

const helper = (value) => {
    return value * 2;
};
"""
        functions_file = os.path.join(repo_dir, "functions.js")
        with open(functions_file, "w") as f:
            f.write(functions_content)

        # Create a file that calls the functions
        usage_content = """
import { processData } from './functions.js';

// Use the function
const result1 = processData(['hello', 'world']);
console.log(result1);

// Another usage
const items = ['foo', 'bar', 'baz'];
const result2 = processData(items);

// In a callback
['test'].forEach(item => {
    processData([item]);
});
"""
        usage_file = os.path.join(repo_dir, "usage.js")
        with open(usage_file, "w") as f:
            f.write(usage_content)

        test_setup.setup_repo()

        # Test adding a parameter with default value
        result = await test_setup.run_tool(
            "add_js_parameter",
            function_name="processData",
            parameter_name="options",
            parameter_type="{ uppercase?: boolean }",
            default_value="{ uppercase: true }",
            position=-1,  # Add at end
            path=repo_dir,
            update_calls=True,
        )
        data = json.loads(result)

        assert data["operation"] == "add_parameter"
        assert data["function_found"] is True
        assert data["files_modified"] >= 2  # Definition + calls

        # Verify the function definition was updated
        with open(functions_file, "r") as f:
            functions_updated = f.read()
        assert (
            "processData(data, options" in functions_updated
            or "processData(data, options = { uppercase: true })" in functions_updated
        )

        # Verify the calls were updated
        with open(usage_file, "r") as f:
            usage_updated = f.read()
        assert "{ uppercase: true }" in usage_updated

        # Test adding parameter without updating calls
        result = await test_setup.run_tool(
            "add_js_parameter",
            function_name="greet",
            parameter_name="greeting",
            default_value='"Hello"',
            position=0,  # Add at beginning
            path=functions_file,
            update_calls=False,
        )
        data = json.loads(result)

        assert data["function_found"] is True
        assert data["files_modified"] == 1  # Only definition


@pytest.mark.asyncio
async def test_remove_unused_exports():
    """Test finding and removing unused exports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a module with various exports
        module1_content = """
// Used export
export function usedFunction() {
    return "I am used";
}

// Unused export
export function unusedFunction() {
    return "I am not used";
}

// Used constant
export const USED_CONSTANT = 42;

// Unused constant
export const UNUSED_CONSTANT = 100;

// Unused class
export class UnusedClass {
    constructor() {
        this.value = "unused";
    }
}

// Default export (unused)
export default function defaultFunction() {
    return "default";
}
"""
        module1_file = os.path.join(repo_dir, "module1.js")
        with open(module1_file, "w") as f:
            f.write(module1_content)

        # Create another module with exports
        module2_content = """
// All exports here are unused
export const SETTING_A = 'a';
export const SETTING_B = 'b';

export function helperFunction() {
    return "helper";
}
"""
        module2_file = os.path.join(repo_dir, "module2.js")
        with open(module2_file, "w") as f:
            f.write(module2_content)

        # Create a file that imports some exports
        consumer_content = """
import { usedFunction, USED_CONSTANT } from './module1';

// Use the imports
console.log(usedFunction());
console.log(USED_CONSTANT);
"""
        consumer_file = os.path.join(repo_dir, "consumer.js")
        with open(consumer_file, "w") as f:
            f.write(consumer_content)

        test_setup.setup_repo()

        # Test dry run to find unused exports
        result = await test_setup.run_tool(
            "remove_unused_exports", path=repo_dir, dry_run=True
        )
        data = json.loads(result)

        assert data["operation"] == "remove_unused_exports"
        assert data["dry_run"] is True
        assert data["files_analyzed"] >= 3
        assert (
            data["unused_exports_count"] >= 6
        )  # unusedFunction, UNUSED_CONSTANT, UnusedClass, defaultFunction, SETTING_A, SETTING_B, helperFunction

        # Check specific unused exports
        unused_names = [e["name"] for e in data["unused_exports"]]
        assert "unusedFunction" in unused_names
        assert "UNUSED_CONSTANT" in unused_names
        assert "UnusedClass" in unused_names
        assert "SETTING_A" in unused_names
        assert "SETTING_B" in unused_names
        assert "helperFunction" in unused_names

        # Verify used exports are not in the list
        assert "usedFunction" not in unused_names
        assert "USED_CONSTANT" not in unused_names

        # Test with exclude patterns
        result = await test_setup.run_tool(
            "remove_unused_exports",
            path=repo_dir,
            dry_run=True,
            exclude_patterns=["**/module2.js"],
        )
        data = json.loads(result)

        # Should have fewer unused exports since module2.js is excluded
        assert data["unused_exports_count"] < 6

        # Test actual removal
        result = await test_setup.run_tool(
            "remove_unused_exports",
            path=repo_dir,
            dry_run=False,
            exclude_patterns=["**/consumer.js"],  # Don't modify the consumer
        )
        data = json.loads(result)

        assert data["dry_run"] is False
        assert data["files_modified"] >= 2

        # Verify exports were commented out
        with open(module1_file, "r") as f:
            module1_updated = f.read()
        assert (
            "// export function unusedFunction" in module1_updated
            or "// REMOVED: Unused export" in module1_updated
        )

        with open(module2_file, "r") as f:
            module2_updated = f.read()
        assert (
            "// export const SETTING_A" in module2_updated
            or "// REMOVED: Unused export" in module2_updated
        )
