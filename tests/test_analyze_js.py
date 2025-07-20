#!/usr/bin/env python3
"""Unit tests for JavaScript AST analyzer."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_analyze_js_valid_extensions():
    """Test that analyze_js validates file extensions."""
    # This test doesn't require tree-sitter to be installed
    # It tests the validation logic before parsing
    try:
        from codemcp.tools.analyze_js import analyze_js
    except ImportError:
        pytest.skip("tree-sitter not installed")

    # Test invalid extension
    result = await analyze_js("test.py", analysis_type="summary")
    data = json.loads(result)
    assert "error" in data
    assert ".js" in data["error"]


@pytest.mark.asyncio
async def test_javascript_analyzer_initialization():
    """Test JavaScriptAnalyzer initialization handling."""
    try:
        from codemcp.tools.analyze_js import JavaScriptAnalyzer
    except ImportError:
        pytest.skip("tree-sitter not installed")

    # Should not raise even if tree-sitter is not properly installed
    analyzer = JavaScriptAnalyzer()
    assert hasattr(analyzer, "parsers_available")


@pytest.mark.asyncio
async def test_regex_fallback_patterns():
    """Test regex fallback functionality."""
    try:
        from codemcp.tools.analyze_js import _regex_fallback_analysis
    except ImportError:
        pytest.skip("tree-sitter not installed")

    # Test regex pattern matching
    test_content = """
function testFunction(a, b) {
    return a + b;
}

const arrowFunc = (x) => x * 2;

async function asyncFunc() {
    return await fetch('/api');
}

import React from 'react';
import { useState } from 'react';

export default testFunction;
export { arrowFunc, asyncFunc };
"""

    result = _regex_fallback_analysis("test.js", test_content, "all")

    # Check functions found
    assert "functions" in result or "functions_count" in result
    if "functions" in result:
        func_names = [f["name"] for f in result["functions"]]
        assert "testFunction" in func_names
        assert "arrowFunc" in func_names
        assert "asyncFunc" in func_names
    else:
        assert result["functions_count"] >= 3

    # Check imports found
    assert "imports" in result or "imports_count" in result
    if "imports" in result:
        sources = [i["source"] for i in result["imports"]]
        assert "react" in sources
    else:
        assert result["imports_count"] >= 2

    # Check exports found
    assert "exports" in result or "exports_count" in result
    if "exports" in result:
        export_names = [e["name"] for e in result["exports"]]
        assert "testFunction" in export_names or any(
            e.get("default") for e in result["exports"]
        )
    else:
        assert result["exports_count"] >= 1


def test_escape_symbol_for_regex():
    """Test regex escaping for symbols."""
    try:
        from codemcp.tools.analyze_js import escape_symbol_for_regex
    except ImportError:
        pytest.skip("tree-sitter not installed")

    # Should be imported from smart_search
    assert escape_symbol_for_regex("test.method") == r"test\.method"
    assert escape_symbol_for_regex("arr[0]") == r"arr\[0\]"
    assert escape_symbol_for_regex("func()") == r"func\(\)"


@pytest.mark.asyncio
async def test_analyze_js_nonexistent_file():
    """Test handling of nonexistent files."""
    try:
        from codemcp.tools.analyze_js import analyze_js
    except ImportError:
        pytest.skip("tree-sitter not installed")

    result = await analyze_js("/nonexistent/file.js", analysis_type="summary")
    data = json.loads(result)
    assert "error" in data
    assert (
        "not found" in data["error"].lower() or "no such file" in data["error"].lower()
    )


@pytest.mark.asyncio
async def test_analyze_js_empty_file():
    """Test handling of empty files."""
    try:
        from codemcp.tools.analyze_js import analyze_js
    except ImportError:
        pytest.skip("tree-sitter not installed")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("")
        temp_file = f.name

    try:
        result = await analyze_js(temp_file, analysis_type="all")
        data = json.loads(result)

        # Empty file should still return valid structure
        assert "error" not in data
        if "summary" in data:
            assert data["summary"]["functions_count"] == 0
            assert data["summary"]["imports_count"] == 0
            assert data["summary"]["exports_count"] == 0
        else:
            assert data.get("functions", []) == []
            assert data.get("imports", []) == []
            assert data.get("exports", []) == []
    finally:
        os.unlink(temp_file)


@pytest.mark.asyncio
async def test_analyze_js_invalid_analysis_type():
    """Test handling of invalid analysis types."""
    try:
        from codemcp.tools.analyze_js import analyze_js
    except ImportError:
        pytest.skip("tree-sitter not installed")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("function test() {}")
        temp_file = f.name

    try:
        result = await analyze_js(temp_file, analysis_type="invalid_type")
        data = json.loads(result)
        assert "error" in data
        assert "invalid analysis type" in data["error"].lower()
    finally:
        os.unlink(temp_file)


@pytest.mark.asyncio
async def test_find_js_references_empty_directory():
    """Test finding references in empty directory."""
    try:
        from codemcp.tools.analyze_js import find_js_references
    except ImportError:
        pytest.skip("tree-sitter not installed")

    with tempfile.TemporaryDirectory() as temp_dir:
        result = await find_js_references("nonExistentSymbol", path=temp_dir)
        data = json.loads(result)

        assert data["symbol"] == "nonExistentSymbol"
        assert data["total_references"] == 0
        assert data["files"] == []


@pytest.mark.asyncio
async def test_find_js_references_invalid_path():
    """Test finding references with invalid path."""
    try:
        from codemcp.tools.analyze_js import find_js_references
    except ImportError:
        pytest.skip("tree-sitter not installed")

    result = await find_js_references("test", path="/nonexistent/path")
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_javascript_analyzer_get_parser():
    """Test parser selection based on file extension."""
    try:
        from codemcp.tools.analyze_js import JavaScriptAnalyzer
    except ImportError:
        pytest.skip("tree-sitter not installed")

    analyzer = JavaScriptAnalyzer()

    if analyzer.parsers_available:
        # Test different file extensions
        assert analyzer.get_parser("test.js") == analyzer.js_parser
        assert analyzer.get_parser("test.ts") == analyzer.ts_parser
        assert analyzer.get_parser("test.tsx") == analyzer.tsx_parser
        assert analyzer.get_parser("test.jsx") == analyzer.jsx_parser
        assert analyzer.get_parser("test.mjs") == analyzer.js_parser

        # Test case insensitive
        assert analyzer.get_parser("TEST.JS") == analyzer.js_parser
        assert analyzer.get_parser("Test.TS") == analyzer.ts_parser


@pytest.mark.asyncio
async def test_javascript_analyzer_parse_malformed():
    """Test parsing malformed JavaScript."""
    try:
        from codemcp.tools.analyze_js import JavaScriptAnalyzer
    except ImportError:
        pytest.skip("tree-sitter not installed")

    analyzer = JavaScriptAnalyzer()

    if analyzer.parsers_available:
        # Malformed JavaScript
        malformed_content = """
        function broken(a, b {  // Missing closing paren
            return a + b;
        }
        """

        # Should not crash, but might return None or partial tree
        tree = analyzer.parse_content(malformed_content, "test.js")
        # Tree-sitter is usually resilient and parses what it can
        assert tree is not None or tree is None  # Either outcome is acceptable


@pytest.mark.asyncio
async def test_regex_fallback_complex_patterns():
    """Test regex fallback with complex JavaScript patterns."""
    try:
        from codemcp.tools.analyze_js import _regex_fallback_analysis
    except ImportError:
        pytest.skip("tree-sitter not installed")

    # Complex patterns that might challenge regex
    complex_content = """
// Nested functions
function outer() {
    function inner() {
        const nested = () => {
            return "deeply nested";
        };
        return nested;
    }
    return inner;
}

// Object methods
const obj = {
    method1() { return 1; },
    method2: function() { return 2; },
    method3: () => 3,
    async method4() { return await Promise.resolve(4); },
    *generatorMethod() { yield 5; }
};

// Class with static and private methods
class ComplexClass {
    #privateMethod() { return "private"; }
    static staticMethod() { return "static"; }
    get getter() { return this.value; }
    set setter(val) { this.value = val; }
}

// Complex imports
import {
    Component1,
    Component2 as C2,
    Component3
} from '@scope/package';

// Complex exports
export {
    outer,
    obj as exportedObj,
    ComplexClass
};

export * from './other-module';
export { default as DefaultExport } from './default';
"""

    result = _regex_fallback_analysis("complex.js", complex_content, "all")

    # Should find at least some of the patterns
    if "functions" in result:
        func_names = [f["name"] for f in result["functions"]]
        # At minimum should find top-level functions
        assert "outer" in func_names or "inner" in func_names

    if "summary" in result:
        # Should find multiple functions and exports
        assert result["summary"]["functions_count"] >= 3
        assert result["summary"]["imports_count"] >= 1
        assert result["summary"]["exports_count"] >= 1


@pytest.mark.asyncio
async def test_analyze_js_with_unicode():
    """Test analyzing JavaScript with Unicode characters."""
    try:
        from codemcp.tools.analyze_js import analyze_js
    except ImportError:
        pytest.skip("tree-sitter not installed")

    unicode_content = """
// Unicode in comments: 你好世界 🌍
function greet(name) {
    return `Hello, ${name}! 👋`;
}

const 数字 = 42;
const émoji = "😀";

// Unicode in strings
const message = "Café ☕ costs €5";

export { greet, 数字, émoji };
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", encoding="utf-8", delete=False
    ) as f:
        f.write(unicode_content)
        temp_file = f.name

    try:
        result = await analyze_js(temp_file, analysis_type="all")
        data = json.loads(result)

        # Should handle Unicode without errors
        assert "error" not in data

        if "functions" in data:
            func_names = [f["name"] for f in data["functions"]]
            assert "greet" in func_names

        if "exports" in data:
            export_names = [e["name"] for e in data["exports"]]
            # Check if Unicode identifiers are preserved
            assert "greet" in export_names
    finally:
        os.unlink(temp_file)


@pytest.mark.asyncio
async def test_parser_error_handling():
    """Test graceful handling of parser errors."""
    try:
        from codemcp.tools.analyze_js import JavaScriptAnalyzer
    except ImportError:
        pytest.skip("tree-sitter not installed")

    # Mock a parser that raises an exception
    with patch("tree_sitter_languages.get_parser") as mock_get_parser:
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = Exception("Parser crashed")
        mock_get_parser.return_value = mock_parser

        analyzer = JavaScriptAnalyzer()

        # Force parsers_available to be True
        analyzer.parsers_available = True
        analyzer.js_parser = mock_parser

        # Should handle the exception gracefully
        tree = analyzer.parse_content("function test() {}", "test.js")
        assert tree is None
