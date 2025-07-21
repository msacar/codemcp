#!/usr/bin/env python3
"""End-to-end tests for analyze_js tool."""

import json
import os
from codemcp.testing import MCPEndToEndTestCase


class AnalyzeJSTest(MCPEndToEndTestCase):
    """Test the analyze_js tool for JavaScript/TypeScript code analysis."""

    async def asyncSetUp(self):
        """Set up the test environment with a git repository."""
        await super().asyncSetUp()

    async def test_analyze_js_function_extraction(self):
        """Test extracting functions from JavaScript file."""
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
        js_file = os.path.join(self.temp_dir.name, "test.js")
        with open(js_file, "w") as f:
            f.write(js_content)

        await self.git_run(["add", "."])
        await self.git_run(["commit", "-m", "Add test files for analyze_js"])

        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)
            result = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "analyze_js",
                    "path": js_file,
                    "analysis_type": "functions",
                    "chat_id": chat_id,
                },
            )
            json_end = result.rfind("}") + 1
            json_part = result[:json_end]
            data = json.loads(json_part)
            functions = data.get("functions", [])
            is_fallback = data.get("fallback_mode", False)

            function_names = [f["name"] for f in functions]
            self.assertIn("regularFunction", function_names)
            self.assertIn("asyncFunction", function_names)
            self.assertIn("arrowFunction", function_names)
            self.assertIn("funcExpression", function_names)
            self.assertIn("method", function_names)
            self.assertIn("asyncMethod", function_names)
            self.assertIn("getValue", function_names)
            self.assertIn("staticMethod", function_names)
            self.assertIn("asyncClassMethod", function_names)
            self.assertIn("exportedFunction", function_names)
            self.assertIn("defaultExport", function_names)

            if not is_fallback:
                regular_func = next(
                    f for f in functions if f["name"] == "regularFunction"
                )
                self.assertEqual(regular_func["type"], "function")
                self.assertEqual(
                    regular_func["params"],
                    [
                        {"name": "a", "optional": False, "default": False},
                        {"name": "b", "optional": False, "default": False},
                    ],
                )
                self.assertFalse(regular_func["async"])

                async_func = next(f for f in functions if f["name"] == "asyncFunction")
                self.assertTrue(async_func["async"])

                static_method = next(
                    f for f in functions if f["name"] == "staticMethod"
                )
                self.assertTrue(static_method["static"])
                self.assertEqual(static_method["class"], "MyClass")
