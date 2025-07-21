#!/usr/bin/env python3
"""
Example script showing how OpenGrok multi-project support works with codemcp.

This demonstrates:
1. How OpenGrok indexes multiple projects
2. How codemcp auto-detects the current project
3. How searches are filtered to the current project
"""

import asyncio


# Simulate being in different project directories
async def demo_multi_project_search():
    print("OpenGrok Multi-Project Search Demo")
    print("=" * 50)

    # Example workspace structure:
    # ~/projects/
    #   ├── webapp/          (project: webapp)
    #   ├── api-service/     (project: api-service)
    #   └── shared-lib/      (project: shared-lib)

    print("\nExample workspace structure:")
    print("~/projects/")
    print("  ├── webapp/          # Auto-detected as 'webapp' project")
    print("  ├── api-service/     # Auto-detected as 'api-service' project")
    print("  └── shared-lib/      # Auto-detected as 'shared-lib' project")

    print("\nHow it works:")
    print("1. OpenGrok indexes ALL projects in the workspace")
    print("2. Each .git directory becomes a separate project")
    print("3. When you run codemcp from webapp/, searches are filtered to 'webapp'")
    print(
        "4. When you run codemcp from api-service/, searches are filtered to 'api-service'"
    )

    print("\nExample searches:")
    print("\nFrom webapp/ directory:")
    print("  opengrok_search('login') -> Searches only in webapp project")
    print("  opengrok_definition_search('UserService') -> Finds definitions in webapp")

    print("\nFrom api-service/ directory:")
    print("  opengrok_search('login') -> Searches only in api-service project")
    print("  opengrok_reference_search('Database') -> Finds references in api-service")

    print("\nBenefits:")
    print("- No need to restart OpenGrok when switching projects")
    print("- Each project maintains its own search index")
    print("- Cross-project searches possible via web UI")
    print("- Automatic project detection based on current directory")


if __name__ == "__main__":
    asyncio.run(demo_multi_project_search())
