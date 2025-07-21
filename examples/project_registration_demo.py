#!/usr/bin/env python3
"""Example: Using project registration with OpenGrok search."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from codemcp.project_registry import get_registry
from codemcp.tools.opengrok_search import check_opengrok_status, opengrok_search


async def main():
    """Demonstrate project registration and OpenGrok search integration."""
    print("=== codemcp Project Registration Example ===\n")

    # Get the registry
    registry = await get_registry()

    # List current projects
    print("📋 Currently registered projects:")
    projects = await registry.list_projects()

    if not projects:
        print("   No projects registered yet.")
        print("\n💡 Register a project with:")
        print("   codemcp project register myproject /path/to/project\n")
    else:
        for proj in projects:
            status = "✅" if proj["exists"] else "❌"
            print(f"   {status} {proj['name']} -> {proj['path']}")

    # Check OpenGrok status
    print("\n🔍 Checking OpenGrok status...")
    if await check_opengrok_status():
        print("   ✅ OpenGrok is running!")

        # Example search if we have projects
        if projects and projects[0]["exists"]:
            proj = projects[0]
            print(f"\n🔎 Example search in project '{proj['name']}':")

            # Simulate a search
            result = await opengrok_search(
                query="TODO", path=proj["path"], max_results=5, chat_id="example-demo"
            )

            print(result)
    else:
        print("   ❌ OpenGrok is not running.")
        print("   Start it with: cd docker/opengrok && docker-compose up -d")

    # Show workspace info
    print(f"\n📁 OpenGrok workspace: {registry.workspace_dir}")
    print("   This directory contains symlinks to all registered projects.")

    # Tips
    print("\n💡 Tips:")
    print("- Register projects from anywhere on your filesystem")
    print("- OpenGrok will index all registered projects automatically")
    print("- Project detection works based on your current directory")
    print("- Use 'codemcp project sync' if you move project directories")


if __name__ == "__main__":
    asyncio.run(main())
