#!/usr/bin/env python3
"""End-to-end tests for OpenGrok search integration."""

import os

import pytest

from codemcp.tools.opengrok_search import (
    check_opengrok_status,
    opengrok_definition_search,
    opengrok_file_search,
    opengrok_reference_search,
    opengrok_search,
)


class TestOpenGrokIntegration:
    """Test OpenGrok search functionality.

    Note: These tests require OpenGrok to be running locally.
    They will be skipped if OpenGrok is not available.
    """

    @pytest.fixture(autouse=True)
    async def check_opengrok_available(self):
        """Skip tests if OpenGrok is not running."""
        if not await check_opengrok_status():
            pytest.skip("OpenGrok is not running - start with ./opengrok.sh start")

    async def test_check_opengrok_status(self):
        """Test that we can check OpenGrok status."""
        # This should pass if we got here (due to fixture)
        status = await check_opengrok_status()
        assert status is True

    async def test_opengrok_search_basic(self):
        """Test basic search functionality."""
        # Search for a common term in the codebase
        result = await opengrok_search(query="def", max_results=10, chat_id="test")

        # Should return results or indicate no results
        assert isinstance(result, str)
        assert len(result) > 0

        # If OpenGrok has indexed the project, we should find Python functions
        if "No results found" not in result:
            assert "def" in result.lower() or "function" in result.lower()

    async def test_opengrok_file_search(self):
        """Test file search functionality."""
        # Search for Python files
        result = await opengrok_file_search(filename="*.py", chat_id="test")

        assert isinstance(result, str)
        assert len(result) > 0

        # Should find Python files if the project is indexed
        if "No files found" not in result:
            assert ".py" in result

    async def test_opengrok_definition_search(self):
        """Test definition search functionality."""
        # Search for a class or function definition
        result = await opengrok_definition_search(symbol="test", chat_id="test")

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_opengrok_reference_search(self):
        """Test reference search functionality."""
        # Search for references to a common symbol
        result = await opengrok_reference_search(symbol="self", chat_id="test")

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_opengrok_search_with_path_filter(self):
        """Test search with path filtering."""
        result = await opengrok_search(
            query="import", path="codemcp", max_results=5, chat_id="test"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_opengrok_search_no_results(self):
        """Test search that should return no results."""
        # Search for something unlikely to exist
        result = await opengrok_search(
            query="xyzzyplughunlikelyterm123456", chat_id="test"
        )

        assert isinstance(result, str)
        assert "No results found" in result

    async def test_opengrok_with_custom_url(self):
        """Test using custom OpenGrok URL from environment."""
        # Save original URL
        original_url = os.environ.get("OPENGROK_URL")

        try:
            # Set custom URL (still pointing to default for test)
            os.environ["OPENGROK_URL"] = "http://localhost:8080/source"

            # Should still work
            status = await check_opengrok_status()
            assert status is True

        finally:
            # Restore original URL
            if original_url is None:
                os.environ.pop("OPENGROK_URL", None)
            else:
                os.environ["OPENGROK_URL"] = original_url
