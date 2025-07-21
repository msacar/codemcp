#!/usr/bin/env python3
"""Project registry for managing multiple projects with different filesystem paths."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
import toml

from .common import get_config_dir


class ProjectRegistry:
    """Manages project name to filesystem path mappings."""

    def __init__(self):
        self.config_dir = get_config_dir()
        self.registry_path = self.config_dir / "projects.toml"
        self.workspace_dir = self.config_dir / "opengrok-workspace"
        self._cache: Optional[Dict[str, str]] = None

    async def ensure_initialized(self):
        """Ensure registry file and workspace directory exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            # Create default registry
            default_config = {"projects": {}}
            async with aiofiles.open(self.registry_path, "w") as f:
                await f.write(toml.dumps(default_config))

    async def load_projects(self) -> Dict[str, str]:
        """Load project mappings from registry."""
        if self._cache is not None:
            return self._cache

        await self.ensure_initialized()

        async with aiofiles.open(self.registry_path, "r") as f:
            content = await f.read()
            config = toml.loads(content)
            self._cache = config.get("projects", {})
            return self._cache

    async def register_project(self, name: str, path: str) -> None:
        """Register a new project or update existing one."""
        # Validate path exists
        project_path = Path(path).expanduser().resolve()
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {path}")

        if not (project_path / ".git").exists():
            logging.warning(f"Warning: {path} does not appear to be a Git repository")

        # Load current projects
        projects = await self.load_projects()
        projects[name] = str(project_path)

        # Save updated registry
        config = {"projects": projects}
        async with aiofiles.open(self.registry_path, "w") as f:
            await f.write(toml.dumps(config))

        # Clear cache
        self._cache = None

        # Update symlink
        await self.update_workspace_symlink(name, project_path)

        logging.info(f"Registered project '{name}' -> {project_path}")

    async def unregister_project(self, name: str) -> None:
        """Remove a project from the registry."""
        projects = await self.load_projects()

        if name not in projects:
            raise ValueError(f"Project '{name}' not found in registry")

        # Remove from registry
        del projects[name]
        config = {"projects": projects}
        async with aiofiles.open(self.registry_path, "w") as f:
            await f.write(toml.dumps(config))

        # Clear cache
        self._cache = None

        # Remove symlink
        symlink_path = self.workspace_dir / name
        if symlink_path.is_symlink():
            symlink_path.unlink()
            logging.info(f"Removed symlink for project '{name}'")

    async def update_workspace_symlink(self, name: str, target_path: Path) -> None:
        """Create or update symlink in OpenGrok workspace."""
        symlink_path = self.workspace_dir / name

        # Remove existing symlink if it exists
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()

        # Create new symlink
        symlink_path.symlink_to(target_path)
        logging.info(f"Created symlink: {symlink_path} -> {target_path}")

    async def sync_workspace(self) -> None:
        """Ensure all registered projects have symlinks in workspace."""
        projects = await self.load_projects()

        # Remove orphaned symlinks
        for item in self.workspace_dir.iterdir():
            if item.is_symlink() and item.name not in projects:
                item.unlink()
                logging.info(f"Removed orphaned symlink: {item}")

        # Create/update symlinks for all projects
        for name, path in projects.items():
            project_path = Path(path)
            if project_path.exists():
                await self.update_workspace_symlink(name, project_path)
            else:
                logging.warning(f"Project path no longer exists: {name} -> {path}")

    async def get_project_for_path(self, path: str) -> Optional[str]:
        """Find which registered project contains the given path."""
        projects = await self.load_projects()

        # Normalize the input path
        target_path = Path(path).expanduser().resolve()

        # Check each project to see if path is within it
        for name, project_path in projects.items():
            project_dir = Path(project_path).expanduser().resolve()
            try:
                # Check if target_path is relative to project_dir
                target_path.relative_to(project_dir)
                return name
            except ValueError:
                # Not a subpath
                continue

        return None

    async def list_projects(self) -> List[Dict[str, str]]:
        """List all registered projects with their paths and status."""
        projects = await self.load_projects()
        result = []

        for name, path in projects.items():
            project_path = Path(path)
            symlink_path = self.workspace_dir / name

            info = {
                "name": name,
                "path": path,
                "exists": project_path.exists(),
                "is_git": (project_path / ".git").exists(),
                "symlink_ok": symlink_path.is_symlink()
                and symlink_path.resolve() == project_path.resolve(),
            }
            result.append(info)

        return result


# Global registry instance
_registry = ProjectRegistry()


async def get_registry() -> ProjectRegistry:
    """Get the global project registry instance."""
    return _registry
