#!/usr/bin/env python3
"""Unit tests for smart search functionality."""

import os
import shutil
import tempfile
import unittest
from unittest import IsolatedAsyncioTestCase

from codemcp.tools.smart_search import (
    JS_TS_PATTERNS,
    USAGE_PATTERNS,
    _determine_definition_type,
    escape_symbol_for_regex,
    get_line_context,
)


class TestSmartSearchPatterns(unittest.TestCase):
    """Test the regex patterns for JavaScript/TypeScript code."""

    def test_class_pattern(self):
        """Test class definition patterns."""
        pattern = JS_TS_PATTERNS["class"].format(symbol="UserManager")

        # Should match various class definitions
        test_cases = [
            ("class UserManager {", True),
            ("export class UserManager {", True),
            ("export default class UserManager {", True),
            ("export abstract class UserManager {", True),
            ("class UserManager<T> {", True),
            ("class UserManager extends BaseClass {", True),
            ("// class UserManager", False),  # Comment
            ("new UserManager()", False),  # Usage, not definition
        ]

        import re

        compiled = re.compile(pattern)
        for code, should_match in test_cases:
            with self.subTest(code=code):
                if should_match:
                    self.assertIsNotNone(compiled.search(code))
                else:
                    self.assertIsNone(compiled.search(code))

    def test_function_pattern(self):
        """Test function definition patterns."""
        pattern = JS_TS_PATTERNS["function"].format(symbol="getData")

        test_cases = [
            ("function getData() {", True),
            ("export function getData() {", True),
            ("export default function getData() {", True),
            ("async function getData() {", True),
            ("export async function getData() {", True),
            ("function getData<T>() {", True),
            ("getData()", False),  # Call, not definition
        ]

        import re

        compiled = re.compile(pattern)
        for code, should_match in test_cases:
            with self.subTest(code=code):
                if should_match:
                    self.assertIsNotNone(compiled.search(code))
                else:
                    self.assertIsNone(compiled.search(code))

    def test_arrow_function_pattern(self):
        """Test arrow function patterns."""
        pattern = JS_TS_PATTERNS["const_function"].format(symbol="getData")

        test_cases = [
            ("const getData = () => {", True),
            ("export const getData = () => {", True),
            ("const getData = async () => {", True),
            ("let getData = (param) => {", True),
            ("var getData = param => {", True),
            ("const getData = async (a, b) => {", True),
        ]

        import re

        compiled = re.compile(pattern)
        for code, should_match in test_cases:
            with self.subTest(code=code):
                if should_match:
                    self.assertIsNotNone(compiled.search(code))

    def test_interface_pattern(self):
        """Test TypeScript interface patterns."""
        pattern = JS_TS_PATTERNS["interface"].format(symbol="User")

        test_cases = [
            ("interface User {", True),
            ("export interface User {", True),
            ("interface User<T> {", True),
            ("interface User extends Base {", True),
            ("// interface User", False),
        ]

        import re

        compiled = re.compile(pattern)
        for code, should_match in test_cases:
            with self.subTest(code=code):
                if should_match:
                    self.assertIsNotNone(compiled.search(code))
                else:
                    self.assertIsNone(compiled.search(code))

    def test_usage_patterns(self):
        """Test usage detection patterns."""
        # Test function call pattern
        pattern = USAGE_PATTERNS["function_call"].format(symbol="getData")
        test_cases = [
            ("getData()", True),
            ("await getData()", True),
            ("result = getData(param)", True),
            ("function getData()", False),  # Definition
            ("class getData", False),  # Definition
        ]

        import re

        compiled = re.compile(pattern)
        for code, should_match in test_cases:
            with self.subTest(code=code, pattern="function_call"):
                if should_match:
                    self.assertIsNotNone(compiled.search(code))
                else:
                    self.assertIsNone(compiled.search(code))

    def test_import_patterns(self):
        """Test import detection patterns."""
        # Named import
        pattern = USAGE_PATTERNS["import_named"].format(symbol="UserManager")
        test_cases = [
            ("import { UserManager } from './user'", True),
            ("import { UserManager, Other } from './user'", True),
            ("import { Other, UserManager } from './user'", True),
            ("import UserManager from './user'", False),  # Default import
        ]

        import re

        compiled = re.compile(pattern)
        for code, should_match in test_cases:
            with self.subTest(code=code):
                if should_match:
                    self.assertIsNotNone(compiled.search(code))
                else:
                    self.assertIsNone(compiled.search(code))


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_escape_symbol_for_regex(self):
        """Test regex escaping for symbols."""
        self.assertEqual(escape_symbol_for_regex("test"), "test")
        self.assertEqual(escape_symbol_for_regex("test.method"), r"test\.method")
        self.assertEqual(escape_symbol_for_regex("test[0]"), r"test\[0\]")

    def test_determine_definition_type(self):
        """Test definition type detection."""
        test_cases = [
            ("class UserManager {", "UserManager", "class"),
            ("interface User {", "User", "interface"),
            ("type UserRole = string", "UserRole", "type"),
            ("enum Status {", "Status", "enum"),
            ("function getData() {", "getData", "function"),
            ("const getData = () => {", "getData", "arrow_function"),
            ("const value = 123", "value", "variable"),
            ("getData() {", "getData", "method"),
        ]

        for line, symbol, expected_type in test_cases:
            with self.subTest(line=line):
                result = _determine_definition_type(line, symbol)
                self.assertEqual(result, expected_type)


class TestGetLineContext(IsolatedAsyncioTestCase):
    """Test the get_line_context function."""

    def setUp(self):
        """Create a temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    async def test_get_line_context_basic(self):
        """Test basic line context extraction."""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.js")
        content = """line 1
class UserManager {
  constructor() {
    this.users = [];
  }
}
line 7"""

        with open(test_file, "w") as f:
            f.write(content)

        # Test finding the class
        pattern = JS_TS_PATTERNS["class"]
        matches = await get_line_context(test_file, pattern, "UserManager")

        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match["line"], 2)
        self.assertEqual(match["text"], "class UserManager {")
        self.assertIn("line 1", match["context"])
        self.assertIn("constructor", match["context"])

    async def test_get_line_context_multiple_matches(self):
        """Test when multiple matches exist in a file."""
        test_file = os.path.join(self.temp_dir, "test.js")
        content = """function getData() {
  return data;
}

const result = getData();

if (getData() !== null) {
  console.log('has data');
}"""

        with open(test_file, "w") as f:
            f.write(content)

        # Test finding function calls
        pattern = USAGE_PATTERNS["function_call"]
        matches = await get_line_context(test_file, pattern, "getData")

        # Should find 2 calls, not the definition
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["line"], 5)
        self.assertEqual(matches[1]["line"], 7)


class TestIntegrationScenarios(IsolatedAsyncioTestCase):
    """Test complete scenarios combining multiple functions."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    async def test_react_component_scenario(self):
        """Test finding React component patterns."""
        test_file = os.path.join(self.temp_dir, "Component.jsx")
        content = """import React from 'react';

export const Button = ({ onClick, children }) => {
  return <button onClick={onClick}>{children}</button>;
};

const IconButton = (props) => (
  <Button {...props}>
    <Icon />
  </Button>
);

export default function App() {
  return (
    <div>
      <Button onClick={() => alert('Hi')}>Click me</Button>
      <IconButton />
    </div>
  );
}"""

        with open(test_file, "w") as f:
            f.write(content)

        # Test finding Button component definition
        pattern = JS_TS_PATTERNS["const_function"]
        matches = await get_line_context(test_file, pattern, "Button")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["line"], 3)

        # Test finding Button usage
        pattern = USAGE_PATTERNS["function_call"]
        matches = await get_line_context(test_file, pattern, "Button")
        self.assertGreater(len(matches), 0)


if __name__ == "__main__":
    unittest.main()
