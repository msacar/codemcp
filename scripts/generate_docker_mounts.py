#!/usr/bin/env python3
"""Generate docker-compose volume mount entries from registered projects."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import codemcp modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from codemcp.project_registry import get_registry


async def main():
    registry = await get_registry()
    projects = await registry.load_projects()

    if not projects:
        print("# No projects registered yet")
        print("# Use 'codemcp project register <name> <path>' to register projects")
        return

    print("# Add these lines to docker/opengrok/docker-compose.yml under volumes:")
    print("#")
    print("# volumes:")

    for name, path in sorted(projects.items()):
        print(f"      - {path}:/opengrok/src/{name}:ro")

    print("\n# After adding these lines, restart OpenGrok:")
    print("# cd ~/codemcp/docker/opengrok")
    print("# docker-compose down")
    print("# docker-compose up -d")


if __name__ == "__main__":
    asyncio.run(main())
