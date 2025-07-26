#!/usr/bin/env python3
"""OpenGrok search integration for advanced code search capabilities."""

import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp

from ..mcp import mcp
from .commit_utils import append_commit_hash

__all__ = [
    "opengrok_search",
    "opengrok_file_search",
    "opengrok_definition_search",
    "opengrok_reference_search",
    "check_opengrok_status",
]

# Default OpenGrok server URL
DEFAULT_OPENGROK_URL = "http://localhost:8080"


async def get_project_name(path: Optional[str] = None) -> Optional[str]:
    """Detect project name from current path.

    First checks the project registry, then falls back to Git detection.
    OpenGrok uses the directory name containing .git as the project name.
    """
    if not path:
        return None

    try:
        # First check project registry
        from ..project_registry import get_registry

        registry = await get_registry()

        project_name = await registry.get_project_for_path(path)
        if project_name:
            logging.debug(f"Found project in registry: {project_name}")
            return project_name

        # Fall back to Git detection
        from ..common import normalize_file_path
        from ..git import find_git_root

        # Normalize the path
        abs_path = normalize_file_path(path)

        # Find git root
        git_root = await find_git_root(abs_path)
        if git_root:
            # Get the project name (last part of the path)
            return os.path.basename(git_root)
    except Exception as e:
        logging.debug(f"Could not determine project name: {e}")

    return None


async def get_opengrok_url() -> str:
    """Get OpenGrok URL from environment or use default."""
    print(os.environ.get("OPENGROK_URL", DEFAULT_OPENGROK_URL))
    return os.environ.get("OPENGROK_URL", DEFAULT_OPENGROK_URL)


async def check_opengrok_status() -> bool:
    """Check if OpenGrok server is available."""
    try:
        url = await get_opengrok_url()
        logging.info(f"Checking OpenGrok status at: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{url}/api/v1/system/ping", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                logging.info(f"OpenGrok ping: {url} -> {response.status}")
                return response.status == 200
    except Exception as e:
        logging.warning(f"OpenGrok unavailable: {e}")

        return False


async def make_opengrok_request(
    endpoint: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Make a request to OpenGrok API."""
    url = await get_opengrok_url()
    full_url = f"{url}/api/v1/{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                full_url, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"OpenGrok API error (status {response.status}): {error_text}"
                    )
                return await response.json()
    except aiohttp.ClientError as e:
        raise Exception(f"Failed to connect to OpenGrok: {e}")


def format_search_result(result: Dict[str, Any]) -> str:
    """Format a single search result for display."""
    path = result.get("path", "Unknown")
    line = result.get("lineNumber", "?")
    content = result.get("line", "").strip()

    # Truncate long lines
    if len(content) > 100:
        content = content[:97] + "..."

    return f"{path}:{line} - {content}"


def format_file_results(
    results: List[Dict[str, Any]], query: str, max_results: int = 50
) -> str:
    """Format file search results."""
    if not results:
        return f"No results found for '{query}'"

    total = len(results)
    displayed = min(total, max_results)

    output = f"Found {total} result(s) for '{query}':\n\n"

    # Group results by file
    files = {}
    for result in results[:displayed]:
        path = result.get("path", "Unknown")
        if path not in files:
            files[path] = []
        files[path].append(result)

    for path, file_results in files.items():
        output += f"\n📄 {path} ({len(file_results)} matches):\n"
        for result in file_results[:5]:  # Show up to 5 matches per file
            line = result.get("lineNumber", "?")
            content = result.get("line", "").strip()
            if len(content) > 80:
                content = content[:77] + "..."
            output += f"  Line {line}: {content}\n"

        if len(file_results) > 5:
            output += f"  ... and {len(file_results) - 5} more matches\n"

    if total > displayed:
        output += f"\n(Showing {displayed} of {total} total results)"

    return output


@mcp.tool()
async def opengrok_search(
    query: str,
    path: Optional[str] = None,
    definition: bool = False,
    symbol: bool = False,
    file_filter: Optional[str] = None,
    max_results: int = 50,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Search code using OpenGrok's powerful search capabilities.

    OpenGrok provides advanced code search with support for:
    - Full text search across all files
    - Symbol search (classes, functions, variables)
    - Definition search
    - Path filtering
    - Regular expressions

    Args:
        query: Search query (supports wildcards *, ?, and regex)
        path: Limit search to specific path/directory
        definition: Search only in definitions
        symbol: Search for symbols (classes, methods, variables)
        file_filter: File path pattern filter (e.g., "*.py", "src/*.js")
        max_results: Maximum number of results to return (default: 50)
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        Formatted search results with file paths and matching lines
    """
    # Check if OpenGrok is available
    if not await check_opengrok_status():
        return "OpenGrok server is not available. Please ensure it's running with 'docker-compose up -d' in the docker/opengrok directory."

    try:
        # Build query parameters
        params = {"q": query}

        if definition:
            params["def"] = query
            params.pop("q", None)
        elif symbol:
            params["symbol"] = query
            params.pop("q", None)

        if path:
            params["path"] = path

            # Auto-detect project from path
            project_name = await get_project_name(path)
            if project_name:
                params["project"] = project_name
                logging.debug(f"Auto-detected project: {project_name}")
            else:
                logging.warning(
                    f"Could not detect project name for path: {path}. Proceeding without project restriction."
                )

        if file_filter:
            params["path"] = file_filter

        # Make the search request
        results = await make_opengrok_request("search", params)

        # Extract search results
        search_results = results.get("results", [])

        # Format the results
        output = format_file_results(search_results, query, max_results)

        # Append commit hash if path is provided
        if path:
            output, _ = await append_commit_hash(output, path, commit_hash)

        return output

    except Exception as e:
        logging.error(f"Error in opengrok_search: {e}", exc_info=True)
        return f"Error performing OpenGrok search: {e}"


@mcp.tool()
async def opengrok_file_search(
    filename: str,
    path: Optional[str] = None,
    exact: bool = False,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Search for files by name using OpenGrok.

    This is more powerful than glob for finding files across large codebases.

    Args:
        filename: File name or pattern to search for
        path: Limit search to specific directory
        exact: Match exact filename (default: False, allows partial matches)
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        List of matching file paths
    """
    if not await check_opengrok_status():
        return "OpenGrok server is not available. Please ensure it's running with 'docker-compose up -d' in the docker/opengrok directory."

    try:
        # For file search, use path parameter
        query = filename if exact else f"*{filename}*"
        params = {"path": query}

        if path:
            params["path"] = f"{path}/{query}"

            # Auto-detect project from path
            project_name = await get_project_name(path)
            if project_name:
                params["project"] = project_name

        # Make the search request
        results = await make_opengrok_request("search", params)

        # Extract unique file paths
        files = set()
        for result in results.get("results", []):
            files.add(result.get("path", ""))

        # Format output
        if not files:
            output = f"No files found matching '{filename}'"
        else:
            output = f"Found {len(files)} file(s) matching '{filename}':\n\n"
            for file_path in sorted(files):
                output += f"📄 {file_path}\n"

        # Append commit hash
        if path:
            output, _ = await append_commit_hash(output, path, commit_hash)

        return output

    except Exception as e:
        logging.error(f"Error in opengrok_file_search: {e}", exc_info=True)
        return f"Error searching for files: {e}"


@mcp.tool()
async def opengrok_definition_search(
    symbol: str,
    language: Optional[str] = None,
    path: Optional[str] = None,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Find where a symbol (class, function, variable) is defined.

    This uses OpenGrok's language-aware parsing for accurate results.

    Args:
        symbol: The symbol name to find definitions for
        language: Limit to specific language (e.g., "python", "javascript")
        path: Limit search to specific directory
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        Locations where the symbol is defined with context
    """
    if not await check_opengrok_status():
        return "OpenGrok server is not available. Please ensure it's running with 'docker-compose up -d' in the docker/opengrok directory."

    try:
        # Search for definitions
        params = {"def": symbol}

        if path:
            params["path"] = path

            # Auto-detect project from path
            project_name = await get_project_name(path)
            if project_name:
                params["project"] = project_name

        # Make the search request
        results = await make_opengrok_request("search", params)

        # Format results focusing on definitions
        search_results = results.get("results", [])

        if not search_results:
            output = f"No definitions found for '{symbol}'"
        else:
            output = f"Found {len(search_results)} definition(s) for '{symbol}':\n\n"

            for result in search_results[:20]:  # Limit to 20 definitions
                file_path = result.get("path", "Unknown")
                line = result.get("lineNumber", "?")
                content = result.get("line", "").strip()

                output += f"📍 {file_path}:{line}\n"
                output += f"   {content}\n\n"

        # Append commit hash
        if path:
            output, _ = await append_commit_hash(output, path, commit_hash)

        return output

    except Exception as e:
        logging.error(f"Error in opengrok_definition_search: {e}", exc_info=True)
        return f"Error searching for definitions: {e}"


@mcp.tool()
async def opengrok_reference_search(
    symbol: str,
    path: Optional[str] = None,
    exclude_definitions: bool = True,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Find all references to a symbol (where it's used, not defined).

    This helps track usage of classes, functions, and variables across the codebase.

    Args:
        symbol: The symbol name to find references for
        path: Limit search to specific directory
        exclude_definitions: Exclude definition locations (default: True)
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        Locations where the symbol is referenced with context
    """
    if not await check_opengrok_status():
        return "OpenGrok server is not available. Please ensure it's running with 'docker-compose up -d' in the docker/opengrok directory."

    try:
        # Search for symbol references
        params = {"refs": symbol}

        project_name = None
        if path:
            params["path"] = path

            # Auto-detect project from path
            project_name = await get_project_name(path)
            if project_name:
                params["project"] = project_name

        # Make the search request
        results = await make_opengrok_request("search", params)

        # If we need to exclude definitions, also get those
        definitions = set()
        if exclude_definitions:
            def_params = {"def": symbol}
            if path:
                def_params["path"] = path
                # Use the same project name for definition search
                if project_name:
                    def_params["project"] = project_name
            def_results = await make_opengrok_request("search", def_params)

            # Create set of definition locations
            for result in def_results.get("results", []):
                location = f"{result.get('path')}:{result.get('lineNumber')}"
                definitions.add(location)

        # Filter and format results
        search_results = results.get("results", [])
        references = []

        for result in search_results:
            location = f"{result.get('path')}:{result.get('lineNumber')}"
            if not exclude_definitions or location not in definitions:
                references.append(result)

        if not references:
            output = f"No references found for '{symbol}'"
        else:
            output = f"Found {len(references)} reference(s) to '{symbol}':\n\n"
            output += format_file_results(references, symbol, max_results=50)

        # Append commit hash
        if path:
            output, _ = await append_commit_hash(output, path, commit_hash)

        return output

    except Exception as e:
        logging.error(f"Error in opengrok_reference_search: {e}", exc_info=True)
        return f"Error searching for references: {e}"
