#!/usr/bin/env python3
"""Unit tests for JavaScript AST analyzer."""

import json

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

    result = await _regex_fallback_analysis("test.js", test_content, "all")

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
