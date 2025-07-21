#!/usr/bin/env python3
"""CLI commands for managing project registration."""

import asyncio
from pathlib import Path

import click
from tabulate import tabulate

from ..project_registry import get_registry


@click.group()
def project_cli():
    """Manage codemcp project registrations."""
    pass


@project_cli.command()
@click.argument("name")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def register(name: str, path: str):
    """Register a project with codemcp.

    Examples:
        codemcp project register myapp /Users/me/projects/myapp
        codemcp project register backend ~/work/backend-api
    """

    async def _register():
        registry = await get_registry()
        try:
            await registry.register_project(name, path)
            click.echo(f"✅ Successfully registered project '{name}' -> {path}")

            # Check if OpenGrok workspace is properly set up
            workspace_dir = registry.workspace_dir
            if not workspace_dir.exists():
                click.echo(
                    f"\n⚠️  OpenGrok workspace directory does not exist: {workspace_dir}"
                )
                click.echo("   Run 'codemcp project sync' to create symlinks")

        except Exception as e:
            click.echo(f"❌ Failed to register project: {e}", err=True)
            raise click.Abort()

    asyncio.run(_register())


@project_cli.command()
@click.argument("name")
def unregister(name: str):
    """Unregister a project from codemcp."""

    async def _unregister():
        registry = await get_registry()
        try:
            await registry.unregister_project(name)
            click.echo(f"✅ Successfully unregistered project '{name}'")
        except ValueError as e:
            click.echo(f"❌ {e}", err=True)
            raise click.Abort()

    asyncio.run(_unregister())


@project_cli.command()
def list():
    """List all registered projects."""

    async def _list():
        registry = await get_registry()
        projects = await registry.list_projects()

        if not projects:
            click.echo("No projects registered yet.")
            click.echo(
                "\nUse 'codemcp project register <name> <path>' to register a project."
            )
            return

        # Prepare table data
        headers = ["Name", "Path", "Status", "Git", "Symlink"]
        rows = []

        for proj in projects:
            status = "✅ OK" if proj["exists"] else "❌ Missing"
            git = "✅" if proj["is_git"] else "⚠️"
            symlink = "✅" if proj["symlink_ok"] else "❌"

            rows.append([proj["name"], proj["path"], status, git, symlink])

        click.echo("\nRegistered Projects:")
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

        # Show workspace location
        click.echo(f"\nOpenGrok workspace: {registry.workspace_dir}")

    asyncio.run(_list())


@project_cli.command()
def sync():
    """Sync workspace symlinks with registered projects."""

    async def _sync():
        registry = await get_registry()
        click.echo("Syncing OpenGrok workspace...")

        try:
            await registry.sync_workspace()

            # Show results
            projects = await registry.list_projects()
            synced = sum(1 for p in projects if p["symlink_ok"])
            total = len(projects)

            click.echo(f"✅ Synced {synced}/{total} projects")

            # Report any issues
            for proj in projects:
                if not proj["exists"]:
                    click.echo(
                        f"⚠️  Project '{proj['name']}' path no longer exists: {proj['path']}"
                    )
                elif not proj["symlink_ok"]:
                    click.echo(f"⚠️  Failed to create symlink for '{proj['name']}'")

        except Exception as e:
            click.echo(f"❌ Sync failed: {e}", err=True)
            raise click.Abort()

    asyncio.run(_sync())


@project_cli.command()
@click.argument("path", type=click.Path(exists=True), default=".")
def which(path: str):
    """Show which project contains the given path."""

    async def _which():
        registry = await get_registry()

        # Convert to absolute path
        abs_path = Path(path).resolve()

        project_name = await registry.get_project_for_path(str(abs_path))

        if project_name:
            projects = await registry.load_projects()
            project_path = projects[project_name]
            click.echo(f"📁 Path belongs to project: {project_name}")
            click.echo(f"   Project root: {project_path}")
        else:
            click.echo(f"❌ Path is not within any registered project: {abs_path}")
            click.echo("\nRegistered projects:")

            projects = await registry.list_projects()
            for proj in projects:
                click.echo(f"  - {proj['name']}: {proj['path']}")

    asyncio.run(_which())


# Export the CLI group
cli = project_cli
