#!/usr/bin/env python3

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import tomli

from ..access import check_edit_permission
from ..common import normalize_file_path
from ..git import is_git_repository
from ..mcp import mcp
from .commit_utils import append_commit_hash

__all__ = [
    "project_overview",
]


@mcp.tool()
async def project_overview(
    path: Optional[str] = None,
    max_depth: int = 3,
    chat_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> str:
    """Get a high-level overview of the project structure.

    This tool respects the project_structure configuration in codemcp.toml.

    Args:
        path: The project directory path (defaults to current directory)
        max_depth: Maximum depth to traverse (default: 3)
        chat_id: The unique ID of the current chat session
        commit_hash: Optional Git commit hash for version tracking

    Returns:
        A formatted project structure overview
    """
    # Set default values
    chat_id = "" if chat_id is None else chat_id

    # Use current directory if no path provided
    if path is None:
        path = os.getcwd()

    # Normalize the directory path
    full_directory_path = normalize_file_path(path)

    # Validate the directory path
    if not os.path.exists(full_directory_path):
        raise FileNotFoundError(f"Directory does not exist: {path}")

    if not os.path.isdir(full_directory_path):
        raise NotADirectoryError(f"Path is not a directory: {path}")

    # Safety check: Verify the directory is within a git repository with codemcp.toml
    if not await is_git_repository(full_directory_path):
        raise ValueError(f"Directory is not in a Git repository: {path}")

    # Check edit permission (which verifies codemcp.toml exists)
    is_permitted, permission_message = await check_edit_permission(full_directory_path)
    if not is_permitted:
        raise ValueError(permission_message)

    # Load project structure configuration
    config = load_project_structure_config(full_directory_path)

    # Generate the overview
    overview = await generate_project_overview(full_directory_path, config, max_depth)

    # Append commit hash
    result, _ = await append_commit_hash(overview, full_directory_path, commit_hash)
    return result


def load_project_structure_config(project_dir: str) -> Dict[str, Any]:
    """Load project structure configuration from codemcp.toml.

    Args:
        project_dir: The project directory path

    Returns:
        Dictionary containing project structure configuration
    """
    config_path = os.path.join(project_dir, "codemcp.toml")
    default_config = {
        "enable_tree_view": True,
        "important_dirs": [],
        "entry_points": [],
        "ignored_dirs": [
            ".git",
            "__pycache__",
            "node_modules",
            ".next",
            ".venv",
            "venv",
            "dist",
            "build",
            "out",
            "target",
            ".idea",
            ".vscode",
            "coverage",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            "htmlcov",
            "*.egg-info",
        ],
        "allowed_extensions": [],  # Empty means all extensions
        "show_file_counts": True,
        "show_file_sizes": False,
    }

    try:
        with open(config_path, "rb") as f:
            toml_config = tomli.load(f)

        if "project_structure" in toml_config:
            ps_config = toml_config["project_structure"]
            # Merge with defaults
            for key, value in ps_config.items():
                if key in default_config:
                    if (
                        isinstance(value, list)
                        and key == "ignored_dirs"
                        and isinstance(default_config[key], list)
                    ):
                        # Extend the default ignored dirs rather than replace
                        default_config[key].extend(value)
                        # Remove duplicates while preserving order
                        default_config[key] = list(dict.fromkeys(default_config[key]))
                    else:
                        default_config[key] = value

    except Exception:
        # If there's any error loading config, use defaults
        pass

    return default_config


async def generate_project_overview(
    project_dir: str, config: Dict[str, Any], max_depth: int
) -> str:
    """Generate the project overview based on configuration.

    Args:
        project_dir: The project directory path
        config: Project structure configuration
        max_depth: Maximum depth to traverse

    Returns:
        Formatted project overview string
    """
    output = []
    output.append("PROJECT STRUCTURE OVERVIEW")
    output.append("=" * 50)
    output.append("")
    output.append(f"📁 Project Root: {project_dir}")
    output.append("")

    # Show entry points if configured
    if config.get("entry_points"):
        output.append("🚀 Entry Points:")
        for entry_point in config["entry_points"]:
            entry_path = os.path.join(project_dir, entry_point)
            if os.path.exists(entry_path):
                output.append(f"  - {entry_point}")
        output.append("")

    # Show important directories if configured
    if config.get("important_dirs"):
        output.append("⭐ Important Directories:")
        for important_dir in config["important_dirs"]:
            dir_path = os.path.join(project_dir, important_dir)
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                file_count = await count_files_in_dir(dir_path, config)
                if config.get("show_file_counts", True):
                    output.append(f"  - {important_dir} ({file_count} files)")
                else:
                    output.append(f"  - {important_dir}")
        output.append("")

    # Generate directory tree
    if config.get("enable_tree_view", True):
        output.append("📂 Directory Structure:")
        tree = await build_directory_tree(project_dir, config, max_depth)
        output.append(format_tree(tree, project_dir))
        output.append("")

    # File statistics
    output.append("📊 Project Statistics:")
    stats = await calculate_project_stats(project_dir, config)
    output.append(f"  Total Directories: {stats['total_dirs']}")
    output.append(f"  Total Files: {stats['total_files']}")

    if config.get("allowed_extensions"):
        output.append("  Files by extension:")
        for ext, count in sorted(stats["files_by_extension"].items()):
            output.append(f"    {ext}: {count}")
    else:
        # Show top 5 extensions by count
        output.append("  Top file types:")
        sorted_exts = sorted(
            stats["files_by_extension"].items(), key=lambda x: x[1], reverse=True
        )[:5]
        for ext, count in sorted_exts:
            output.append(f"    {ext}: {count}")

    return "\n".join(output)


async def build_directory_tree(
    root_path: str, config: Dict[str, Any], max_depth: int, current_depth: int = 0
) -> List[Dict[str, Any]]:
    """Build a directory tree structure.

    Args:
        root_path: The root directory path
        config: Project structure configuration
        max_depth: Maximum depth to traverse
        current_depth: Current traversal depth

    Returns:
        List of tree nodes
    """
    if current_depth >= max_depth:
        return []

    tree = []
    ignored_dirs = set(config.get("ignored_dirs", []))
    allowed_extensions = set(config.get("allowed_extensions", []))

    try:
        entries = sorted(os.listdir(root_path))

        for entry in entries:
            entry_path = os.path.join(root_path, entry)

            # Skip hidden files/dirs unless explicitly included
            if entry.startswith(".") and entry not in [".github", ".gitlab"]:
                if entry not in config.get("important_dirs", []):
                    continue

            if os.path.isdir(entry_path):
                # Skip ignored directories
                if entry in ignored_dirs:
                    continue

                node = {
                    "name": entry,
                    "type": "directory",
                    "children": await build_directory_tree(
                        entry_path, config, max_depth, current_depth + 1
                    ),
                }

                if config.get("show_file_counts", True):
                    node["file_count"] = await count_files_in_dir(entry_path, config)

                tree.append(node)

            else:
                # Check file extension if filters are set
                if allowed_extensions:
                    ext = Path(entry).suffix
                    if ext not in allowed_extensions:
                        continue

                node = {"name": entry, "type": "file"}

                if config.get("show_file_sizes", False):
                    node["size"] = os.path.getsize(entry_path)

                tree.append(node)

    except PermissionError:
        pass

    return tree


async def count_files_in_dir(dir_path: str, config: Dict[str, Any]) -> int:
    """Count files in a directory recursively.

    Args:
        dir_path: Directory path to count files in
        config: Project structure configuration

    Returns:
        Number of files
    """
    count = 0
    ignored_dirs = set(config.get("ignored_dirs", []))
    allowed_extensions = set(config.get("allowed_extensions", []))

    for root, dirs, files in os.walk(dir_path):
        # Remove ignored directories from dirs to prevent descending into them
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

        if allowed_extensions:
            count += sum(1 for f in files if Path(f).suffix in allowed_extensions)
        else:
            count += len([f for f in files if not f.startswith(".")])

    return count


async def calculate_project_stats(
    project_dir: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate project statistics.

    Args:
        project_dir: The project directory path
        config: Project structure configuration

    Returns:
        Dictionary containing project statistics
    """
    stats: Dict[str, Any] = {
        "total_dirs": 0,
        "total_files": 0,
        "files_by_extension": {},
    }

    ignored_dirs = set(config.get("ignored_dirs", []))
    allowed_extensions = set(config.get("allowed_extensions", []))

    for root, dirs, files in os.walk(project_dir):
        # Remove ignored directories
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

        stats["total_dirs"] += len(dirs)

        for file in files:
            if file.startswith("."):
                continue

            ext = Path(file).suffix or "(no extension)"

            if allowed_extensions and ext not in allowed_extensions:
                continue

            stats["total_files"] += 1
            files_by_ext = stats["files_by_extension"]
            files_by_ext[ext] = files_by_ext.get(ext, 0) + 1

    return stats


def format_tree(tree: List[Dict[str, Any]], root_path: str, prefix: str = "") -> str:
    """Format the tree structure for display.

    Args:
        tree: Tree structure to format
        root_path: Root directory path
        prefix: Prefix for indentation

    Returns:
        Formatted tree string
    """
    lines = []

    for i, node in enumerate(tree):
        is_last = i == len(tree) - 1
        current_prefix = "└── " if is_last else "├── "
        next_prefix = "    " if is_last else "│   "

        name = node["name"]
        if node["type"] == "directory":
            name += "/"
            if "file_count" in node:
                name += f" ({node['file_count']} files)"

        lines.append(f"{prefix}{current_prefix}{name}")

        if node.get("children"):
            child_lines = format_tree(node["children"], root_path, prefix + next_prefix)
            lines.append(child_lines)

    return "\n".join(lines)
