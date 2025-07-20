#!/usr/bin/env python3
"""Additional end-to-end tests for analyze_js tool edge cases and complex scenarios."""

import json
import os
import tempfile

import pytest

from codemcp.testing import TestSetup


@pytest.mark.asyncio
async def test_analyze_js_with_jsx_components():
    """Test analyzing React JSX components with complex patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a complex React component
        jsx_content = """
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import { withRouter } from 'react-router-dom';
import styled from 'styled-components';

// Styled component
const StyledButton = styled.button`
    background: ${props => props.primary ? 'blue' : 'gray'};
    color: white;
    padding: 10px;
`;

// Higher-order component
const withAuthentication = (Component) => {
    return function AuthenticatedComponent(props) {
        const [isAuthenticated, setIsAuthenticated] = useState(false);

        useEffect(() => {
            // Check authentication
            checkAuth().then(setIsAuthenticated);
        }, []);

        if (!isAuthenticated) return <div>Please login</div>;
        return <Component {...props} />;
    };
};

// Forward ref component
const FancyButton = React.forwardRef((props, ref) => (
    <button ref={ref} className="fancy-button">
        {props.children}
    </button>
));

// Main component with various hooks and patterns
const ComplexComponent = ({
    title,
    items = [],
    onItemClick,
    ...restProps
}) => {
    // State hooks
    const [selectedItem, setSelectedItem] = useState(null);
    const [filter, setFilter] = useState('');

    // Memoized values
    const filteredItems = useMemo(() => {
        return items.filter(item =>
            item.name.toLowerCase().includes(filter.toLowerCase())
        );
    }, [items, filter]);

    // Callback hooks
    const handleItemClick = useCallback((item) => {
        setSelectedItem(item);
        onItemClick?.(item);
    }, [onItemClick]);

    // Custom hook
    const useWindowSize = () => {
        const [size, setSize] = useState({ width: 0, height: 0 });

        useEffect(() => {
            const handleResize = () => {
                setSize({ width: window.innerWidth, height: window.innerHeight });
            };

            window.addEventListener('resize', handleResize);
            handleResize();

            return () => window.removeEventListener('resize', handleResize);
        }, []);

        return size;
    };

    const windowSize = useWindowSize();

    // Render prop pattern
    const DataProvider = ({ render }) => {
        const data = useFetchData();
        return render(data);
    };

    return (
        <div className="complex-component" {...restProps}>
            <h1>{title}</h1>
            <input
                type="text"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter items..."
            />

            <DataProvider
                render={(data) => (
                    <div>Data: {JSON.stringify(data)}</div>
                )}
            />

            <ul>
                {filteredItems.map((item, index) => (
                    <li key={item.id || index} onClick={() => handleItemClick(item)}>
                        {item.name}
                        {selectedItem?.id === item.id && <span> (selected)</span>}
                    </li>
                ))}
            </ul>

            <StyledButton primary onClick={() => console.log('Clicked')}>
                Primary Button
            </StyledButton>

            <FancyButton ref={buttonRef}>
                Fancy Button
            </FancyButton>

            <div>Window size: {windowSize.width} x {windowSize.height}</div>
        </div>
    );
};

// Class component for comparison
class ClassComponent extends React.Component {
    static propTypes = {
        message: PropTypes.string.isRequired
    };

    static defaultProps = {
        message: 'Hello'
    };

    constructor(props) {
        super(props);
        this.state = {
            count: 0
        };
        this.handleClick = this.handleClick.bind(this);
    }

    componentDidMount() {
        console.log('Mounted');
    }

    componentDidUpdate(prevProps, prevState) {
        if (prevState.count !== this.state.count) {
            console.log('Count changed');
        }
    }

    handleClick() {
        this.setState(prevState => ({ count: prevState.count + 1 }));
    }

    render() {
        return (
            <div onClick={this.handleClick}>
                {this.props.message}: {this.state.count}
            </div>
        );
    }
}

// Connect to Redux
const mapStateToProps = (state) => ({
    user: state.user,
    settings: state.settings
});

const mapDispatchToProps = {
    updateUser: (data) => ({ type: 'UPDATE_USER', payload: data })
};

export default connect(mapStateToProps, mapDispatchToProps)(
    withRouter(withAuthentication(ComplexComponent))
);

export { ClassComponent, FancyButton, StyledButton };
"""
        jsx_file = os.path.join(repo_dir, "ComplexComponent.jsx")
        with open(jsx_file, "w") as f:
            f.write(jsx_content)

        test_setup.setup_repo()

        # Test full analysis
        result = await test_setup.run_tool(
            "analyze_js", path="ComplexComponent.jsx", analysis_type="all"
        )
        data = json.loads(result)

        # Check functions and components
        functions = data["functions"]
        function_names = [f["name"] for f in functions]

        # Should find various function patterns
        assert "withAuthentication" in function_names
        assert "AuthenticatedComponent" in function_names
        assert "ComplexComponent" in function_names
        assert "handleItemClick" in function_names
        assert "useWindowSize" in function_names
        assert "DataProvider" in function_names

        # Check classes
        classes = data["classes"]
        class_names = [c["name"] for c in classes]
        assert "ClassComponent" in class_names

        # Check methods in class
        class_methods = [f for f in functions if f.get("class") == "ClassComponent"]
        method_names = [m["name"] for m in class_methods]
        assert "componentDidMount" in method_names
        assert "componentDidUpdate" in method_names
        assert "handleClick" in method_names
        assert "render" in method_names

        # Check imports
        imports = data["imports"]
        react_imports = [i for i in imports if i["source"] == "react"]
        assert len(react_imports) > 0

        # Check exports
        exports = data["exports"]
        export_names = [e["name"] for e in exports]
        assert "ClassComponent" in export_names
        assert "FancyButton" in export_names
        assert "StyledButton" in export_names


@pytest.mark.asyncio
async def test_analyze_js_edge_case_syntax():
    """Test analyzing JavaScript with edge case syntax patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create file with edge case syntax
        edge_case_content = r"""
// Template literal tag functions
function myTag(strings, ...values) {
    return strings.reduce((result, str, i) =>
        result + str + (values[i] || ''), ''
    );
}

const result = myTag`Hello ${name}, you are ${age} years old`;

// Computed property names
const propKey = 'dynamicKey';
const obj = {
    [propKey]: 'value',
    [`computed_${propKey}`]: 'another value',
    [Symbol.iterator]: function* () {
        yield 1;
        yield 2;
    }
};

// Destructuring with defaults and renaming
function complexParams({
    name: userName = 'Anonymous',
    age = 0,
    address: { city = 'Unknown', ...addressRest } = {},
    ...rest
}) {
    console.log(userName, age, city, addressRest, rest);
}

// Generator functions and async generators
function* generator() {
    yield 1;
    yield* [2, 3, 4];
    return 5;
}

async function* asyncGenerator() {
    for (let i = 0; i < 5; i++) {
        await new Promise(resolve => setTimeout(resolve, 100));
        yield i;
    }
}

// Class with private fields and static blocks
class ModernClass {
    #privateField = 42;
    static #privateStatic = 'secret';

    static {
        // Static initialization block
        console.log('Class initialized');
        this.#privateStatic = 'initialized';
    }

    get #privateGetter() {
        return this.#privateField;
    }

    set #privateSetter(value) {
        this.#privateField = value;
    }

    #privateMethod() {
        return this.#privateGetter;
    }

    publicMethod() {
        return this.#privateMethod();
    }
}

// Dynamic imports
const loadModule = async () => {
    const { default: module } = await import('./dynamic-module.js');
    return module;
};

// Optional chaining and nullish coalescing
const deepValue = obj?.nested?.property ?? 'default';
const funcResult = obj.method?.() ?? 'no method';

// BigInt and numeric separators
const bigNumber = 123_456_789n;
const binary = 0b1010_0001_1000_0101;
const hex = 0xFF_EC_DE_5E;

// Logical assignment operators
let x = null;
x ||= 'default';
x &&= 'new value';
x ??= 'fallback';

// Export patterns with renaming
export {
    generator as gen,
    asyncGenerator as asyncGen,
    ModernClass as default
};

// Re-export with renaming
export { someFunc as renamedFunc } from './other-module';
export * as utils from './utils';
"""
        edge_case_file = os.path.join(repo_dir, "edge_cases.js")
        with open(edge_case_file, "w") as f:
            f.write(edge_case_content)

        test_setup.setup_repo()

        # Test analysis
        result = await test_setup.run_tool(
            "analyze_js", path="edge_cases.js", analysis_type="all"
        )
        data = json.loads(result)

        # Check various patterns were detected
        functions = data["functions"]
        function_names = [f["name"] for f in functions]

        assert "myTag" in function_names
        assert "complexParams" in function_names
        assert "generator" in function_names
        assert "asyncGenerator" in function_names
        assert "loadModule" in function_names

        # Check generator functions
        generator_func = next(f for f in functions if f["name"] == "generator")
        assert generator_func.get("generator", False) or "generator" in str(
            generator_func
        )

        async_gen = next(f for f in functions if f["name"] == "asyncGenerator")
        assert async_gen.get("async", False)

        # Check class with private members
        classes = data["classes"]
        modern_class = next((c for c in classes if c["name"] == "ModernClass"), None)
        assert modern_class is not None

        # Check exports with renaming
        exports = data["exports"]
        assert any(
            e.get("name") == "generator" or e.get("alias") == "gen" for e in exports
        )
        assert any(e.get("default", False) for e in exports)


@pytest.mark.asyncio
async def test_rename_js_symbol_complex_scenarios():
    """Test renaming symbols in complex scenarios."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create files with complex naming scenarios

        # File 1: Symbol used in various contexts
        context_file_content = """
// Define a class
class DataManager {
    constructor() {
        this.DataManager = 'self-reference';  // Property with same name
    }

    static DataManager = 'static property';  // Static property

    processDataManager() {  // Method with symbol in name
        return this.DataManager;
    }
}

// Function with same name
function DataManager() {
    return new DataManager();  // Recursive reference
}

// Variable with same name in different scope
{
    const DataManager = 'local variable';
    console.log(DataManager);
}

// Use as type (TypeScript)
let manager: DataManager;

// Use in JSX
const Component = () => {
    return (
        <div>
            <DataManager />
            <DataManager.Provider>
                <span>Content</span>
            </DataManager.Provider>
        </div>
    );
};

// Export various forms
export { DataManager };
export default DataManager;
export { DataManager as Manager };
"""
        context_file = os.path.join(repo_dir, "contexts.js")
        with open(context_file, "w") as f:
            f.write(context_file_content)

        # File 2: Importing and using the symbol
        import_file_content = """
import DataManager, { DataManager as DM } from './contexts';
import { Manager } from './contexts';

// Use in different ways
const instance = new DataManager();
const func = DataManager();
const Class = DataManager;

// Method calls
instance.processDataManager();

// Property access
console.log(DataManager.DataManager);

// Destructuring
const { DataManager: LocalDM } = { DataManager };

// Template literal
const message = `Using ${DataManager} here`;

// Comments should not be changed
// DataManager is a class for managing data
/* DataManager handles all data operations */
"""
        import_file = os.path.join(repo_dir, "imports.js")
        with open(import_file, "w") as f:
            f.write(import_file_content)

        test_setup.setup_repo()

        # Test renaming with dry run first
        result = await test_setup.run_tool(
            "rename_js_symbol",
            old_name="DataManager",
            new_name="DataController",
            path=repo_dir,
            dry_run=True,
        )
        data = json.loads(result)

        assert data["dry_run"] is True
        assert data["total_files"] >= 2
        assert data["total_replacements"] > 10  # Many occurrences

        # Check that it identifies different contexts
        preview = data.get("preview", [])
        contexts_found = set()
        for file_preview in preview:
            for change in file_preview.get("changes", []):
                if "context" in change:
                    contexts_found.add(change["context"])

        # Should identify multiple contexts
        assert len(contexts_found) > 3


@pytest.mark.asyncio
async def test_add_parameter_typescript_types():
    """Test adding parameters with TypeScript type annotations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create TypeScript file with typed functions
        ts_content = """
interface User {
    id: number;
    name: string;
    email: string;
}

interface Options {
    includeEmail?: boolean;
    format?: 'json' | 'xml';
}

// Generic function
function processUser<T extends User>(user: T): string {
    return `User: ${user.name}`;
}

// Async function with multiple params
async function fetchUserData(
    userId: number,
    options?: Partial<Options>
): Promise<User | null> {
    const response = await fetch(`/api/users/${userId}`);
    if (!response.ok) return null;
    return response.json();
}

// Arrow function with destructured params
const formatUser = ({ name, email }: User): string => {
    return `${name} <${email}>`;
};

// Class method
class UserService {
    async updateUser(
        userId: number,
        updates: Partial<User>
    ): Promise<boolean> {
        try {
            await this.api.patch(`/users/${userId}`, updates);
            return true;
        } catch {
            return false;
        }
    }
}

// Function overloads
function findUser(id: number): User | undefined;
function findUser(email: string): User | undefined;
function findUser(predicate: (user: User) => boolean): User | undefined;
function findUser(arg: number | string | ((user: User) => boolean)): User | undefined {
    // Implementation
    return undefined;
}

// Usage
const user = processUser({ id: 1, name: 'John', email: 'john@example.com' });
const data = await fetchUserData(123);
const formatted = formatUser({ id: 2, name: 'Jane', email: 'jane@example.com' });

const service = new UserService();
await service.updateUser(1, { name: 'Updated' });

const found = findUser(123);
const found2 = findUser('john@example.com');
const found3 = findUser(u => u.name === 'John');
"""
        ts_file = os.path.join(repo_dir, "users.ts")
        with open(ts_file, "w") as f:
            f.write(ts_content)

        test_setup.setup_repo()

        # Test adding parameter with TypeScript type
        result = await test_setup.run_tool(
            "add_js_parameter",
            function_name="processUser",
            parameter_name="options",
            parameter_type="Options",
            default_value="{}",
            position=-1,
            path=repo_dir,
            update_calls=True,
        )
        data = json.loads(result)

        assert data["functions_updated"] >= 1
        assert data["calls_updated"] >= 1

        # Verify the parameter was added with type
        with open(ts_file, "r") as f:
            updated_content = f.read()

        # Should have added the typed parameter
        assert (
            "options: Options" in updated_content
            or "options?: Options" in updated_content
        )

        # Test adding parameter to async function
        result = await test_setup.run_tool(
            "add_js_parameter",
            function_name="fetchUserData",
            parameter_name="signal",
            parameter_type="AbortSignal",
            position=-1,
            path=repo_dir,
            update_calls=False,  # Don't update calls this time
        )
        data = json.loads(result)

        assert data["functions_updated"] >= 1


@pytest.mark.asyncio
async def test_remove_unused_exports_circular_dependencies():
    """Test removing unused exports with circular dependencies."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create circular dependency scenario

        # moduleA.js - exports used by moduleB
        module_a_content = """
import { helperB } from './moduleB.js';

export function helperA() {
    return "Helper A";
}

export function unusedInA() {
    return "This is not used anywhere";
}

export function usedByB() {
    return helperB() + " from A";
}
"""
        module_a = os.path.join(repo_dir, "moduleA.js")
        with open(module_a, "w") as f:
            f.write(module_a_content)

        # moduleB.js - exports used by moduleA
        module_b_content = """
import { helperA, usedByB } from './moduleA.js';

export function helperB() {
    return "Helper B";
}

export function unusedInB() {
    return "Also not used";
}

export function circularUsage() {
    return helperA() + usedByB();
}
"""
        module_b = os.path.join(repo_dir, "moduleB.js")
        with open(module_b, "w") as f:
            f.write(module_b_content)

        # moduleC.js - uses some exports
        module_c_content = """
import { circularUsage } from './moduleB.js';

console.log(circularUsage());

// Only uses one function from the circular modules
"""
        module_c = os.path.join(repo_dir, "moduleC.js")
        with open(module_c, "w") as f:
            f.write(module_c_content)

        test_setup.setup_repo()

        # Test finding unused exports
        result = await test_setup.run_tool(
            "remove_unused_exports", path=repo_dir, dry_run=True
        )
        data = json.loads(result)

        # Should correctly identify unused exports
        unused_names = [e["name"] for e in data["unused_exports"]]
        assert "unusedInA" in unused_names
        assert "unusedInB" in unused_names

        # Should not mark exports used in circular dependencies as unused
        assert "helperA" not in unused_names
        assert "helperB" not in unused_names
        assert "usedByB" not in unused_names


@pytest.mark.asyncio
async def test_find_references_in_large_codebase():
    """Test finding references efficiently in a larger codebase."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create a directory structure
        os.makedirs(os.path.join(repo_dir, "src", "components"))
        os.makedirs(os.path.join(repo_dir, "src", "utils"))
        os.makedirs(os.path.join(repo_dir, "src", "services"))
        os.makedirs(os.path.join(repo_dir, "tests"))

        # Create a commonly used utility
        common_util_content = """
export const CONFIG = {
    API_URL: 'https://api.example.com',
    TIMEOUT: 5000
};

export function request(url, options = {}) {
    return fetch(CONFIG.API_URL + url, {
        ...options,
        timeout: CONFIG.TIMEOUT
    });
}

export class Logger {
    static log(message) {
        console.log(`[LOG] ${message}`);
    }

    static error(message) {
        console.error(`[ERROR] ${message}`);
    }
}
"""
        util_file = os.path.join(repo_dir, "src", "utils", "common.js")
        with open(util_file, "w") as f:
            f.write(common_util_content)

        # Create multiple files that use the utility
        for i in range(5):
            component_content = f"""
import {{ CONFIG, request, Logger }} from '../utils/common';

export function Component{i}() {{
    Logger.log('Component{i} initialized');

    const fetchData = async () => {{
        try {{
            const data = await request('/endpoint{i}');
            Logger.log('Data fetched');
            return data;
        }} catch (err) {{
            Logger.error('Failed to fetch');
            throw err;
        }}
    }};

    return {{
        name: 'Component{i}',
        apiUrl: CONFIG.API_URL,
        fetchData
    }};
}}

// Also use CONFIG directly
console.log('API URL:', CONFIG.API_URL);
console.log('Timeout:', CONFIG.TIMEOUT);
"""
            component_file = os.path.join(
                repo_dir, "src", "components", f"Component{i}.js"
            )
            with open(component_file, "w") as f:
                f.write(component_content)

        # Create service files
        for i in range(3):
            service_content = f"""
import {{ Logger, request }} from '../utils/common';

export class Service{i} {{
    constructor() {{
        Logger.log('Service{i} created');
    }}

    async getData() {{
        return request('/service{i}/data');
    }}
}}

// Some services also use CONFIG
import {{ CONFIG }} from '../utils/common';
const timeout = CONFIG.TIMEOUT;
"""
            service_file = os.path.join(repo_dir, "src", "services", f"Service{i}.js")
            with open(service_file, "w") as f:
                f.write(service_content)

        # Create test files
        test_content = """
import { Logger } from '../src/utils/common';

describe('Logger tests', () => {
    it('should log messages', () => {
        Logger.log('Test message');
        Logger.error('Test error');
    });
});
"""
        test_file = os.path.join(repo_dir, "tests", "logger.test.js")
        with open(test_file, "w") as f:
            f.write(test_content)

        test_setup.setup_repo()

        # Test finding references to CONFIG
        result = await test_setup.run_tool(
            "find_js_references", symbol="CONFIG", path=repo_dir
        )
        data = json.loads(result)

        assert data["symbol"] == "CONFIG"
        assert data["files_analyzed"] >= 9  # All created files
        assert data["total_references"] >= 15  # Multiple uses across files

        # Check context breakdown
        contexts = data["references_by_context"]
        assert "property_access" in contexts  # CONFIG.API_URL, CONFIG.TIMEOUT
        assert "import" in contexts  # Import statements

        # Test finding Logger references with context filter
        result = await test_setup.run_tool(
            "find_js_references",
            symbol="Logger",
            path=repo_dir,
            context_filter="property_access",
        )
        data = json.loads(result)

        # Should only find Logger.log and Logger.error calls
        assert data["context_filter"] == "property_access"
        assert data["total_references"] >= 10  # Multiple Logger.log/error calls


@pytest.mark.asyncio
async def test_analyze_js_web_worker_and_node_patterns():
    """Test analyzing Web Worker and Node.js specific patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_setup = TestSetup(temp_dir)
        repo_dir = test_setup.repo_dir

        # Create Web Worker file
        worker_content = """
// Web Worker file
self.addEventListener('message', function(e) {
    const { type, data } = e.data;

    switch (type) {
        case 'PROCESS':
            const result = processData(data);
            self.postMessage({ type: 'RESULT', data: result });
            break;

        case 'TERMINATE':
            self.close();
            break;
    }
});

function processData(data) {
    // Heavy computation
    return data.map(item => item * 2);
}

// Worker-specific globals
console.log(self.location);
importScripts('utils.js', 'helpers.js');

// Shared Array Buffer handling
const sharedBuffer = new SharedArrayBuffer(1024);
const sharedArray = new Int32Array(sharedBuffer);

Atomics.add(sharedArray, 0, 1);
Atomics.wait(sharedArray, 0, 0);
"""
        worker_file = os.path.join(repo_dir, "worker.js")
        with open(worker_file, "w") as f:
            f.write(worker_content)

        # Create Node.js specific file
        node_content = """
// Node.js specific patterns
const fs = require('fs').promises;
const path = require('path');
const { Worker } = require('worker_threads');
const cluster = require('cluster');

// Module exports patterns
module.exports = {
    processFile,
    startWorker
};

module.exports.helper = helperFunction;

async function processFile(filePath) {
    const data = await fs.readFile(filePath, 'utf8');
    return data.split('\\n').length;
}

function startWorker() {
    if (cluster.isMaster) {
        console.log(`Master ${process.pid} is running`);

        // Fork workers
        for (let i = 0; i < require('os').cpus().length; i++) {
            cluster.fork();
        }

        cluster.on('exit', (worker, code, signal) => {
            console.log(`Worker ${worker.process.pid} died`);
        });
    } else {
        // Worker process
        require('./server.js');
    }
}

function helperFunction() {
    return __dirname + path.sep + __filename;
}

// Global Node.js objects
process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
});

// Buffer operations
const buf = Buffer.from('hello world', 'utf8');
console.log(buf.toString('hex'));

// ES modules in Node.js
export async function modernExport() {
    const { readFile } = await import('fs/promises');
    return readFile;
}

// Top-level await (Node.js 14.8+)
const config = await fs.readFile('./config.json', 'utf8');
"""
        node_file = os.path.join(repo_dir, "node-specific.js")
        with open(node_file, "w") as f:
            f.write(node_content)

        test_setup.setup_repo()

        # Test analyzing worker file
        result = await test_setup.run_tool(
            "analyze_js", path="worker.js", analysis_type="all"
        )
        data = json.loads(result)

        functions = data["functions"]
        function_names = [f["name"] for f in functions]
        assert "processData" in function_names

        # Should detect the event listener function
        assert any(
            "message" in str(f) or f.get("type") == "function_expression"
            for f in functions
        )

        # Test analyzing Node.js file
        result = await test_setup.run_tool(
            "analyze_js", path="node-specific.js", analysis_type="all"
        )
        data = json.loads(result)

        functions = data["functions"]
        function_names = [f["name"] for f in functions]
        assert "processFile" in function_names
        assert "startWorker" in function_names
        assert "helperFunction" in function_names
        assert "modernExport" in function_names

        # Check for require imports (CommonJS)
        imports = data["imports"]
        assert any(i.get("type") == "require" or "fs" in i["source"] for i in imports)

        # Check mixed export patterns
        exports = data["exports"]
        assert len(exports) >= 3  # module.exports, named exports, ES export
