#!/usr/bin/env python3
"""Generate docker-compose override file for registered projects."""

import asyncio
import sys
from pathlib import Path

import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from codemcp.project_registry import get_registry


async def generate_override():
    """Generate docker-compose.override.yml with direct project mounts."""
    registry = await get_registry()
    projects = await registry.load_projects()

    if not projects:
        print("No projects registered. Register projects first with:")
        print("  codemcp project register <name> <path>")
        return

    # Create override configuration
    override = {"version": "3.8", "services": {"opengrok": {"volumes": []}}}

    # Add each project as a direct mount
    for name, path in projects.items():
        if Path(path).exists():
            # Mount each project directly into /opengrok/src/<project-name>
            mount = f"{path}:/opengrok/src/{name}:ro"
            override["services"]["opengrok"]["volumes"].append(mount)
            print(f"✅ Adding mount: {name} -> {path}")
        else:
            print(f"⚠️  Skipping {name}: path {path} doesn't exist")

    # Add the other required volumes
    override["services"]["opengrok"]["volumes"].extend(
        [
            "opengrok-data:/opengrok/data",
            "./logging.properties:/opengrok/etc/logging.properties:ro",
        ]
    )

    # Write override file
    override_path = (
        Path(__file__).parent.parent
        / "docker"
        / "opengrok"
        / "docker-compose.override.yml"
    )
    with open(override_path, "w") as f:
        yaml.dump(override, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Generated {override_path}")
    print("\nNext steps:")
    print("1. cd docker/opengrok")
    print("2. docker-compose down")
    print("3. docker volume rm codemcp-opengrok-data")
    print("4. docker-compose up -d")
    print(
        "\nDocker will automatically use both docker-compose.yml and docker-compose.override.yml"
    )


if __name__ == "__main__":
    print("🔧 Generating Docker Compose override for registered projects...")
    asyncio.run(generate_override())
