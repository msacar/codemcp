#!/usr/bin/env python3
"""Tests for project registry functionality.

NOTE: These tests were written for the symlink-based implementation.
They need to be updated for the current bind mount approach where:
- No symlinks are created
- register_project returns instructions instead of creating symlinks
- sync_workspace functionality is removed
"""

import tempfile
from pathlib import Path

import pytest
import toml

from codemcp.project_registry import ProjectRegistry


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_config_dir, monkeypatch):
    """Create a project registry with temporary config directory."""
    # Monkey patch the get_config_dir function
    monkeypatch.setattr(
        "codemcp.project_registry.get_config_dir", lambda: temp_config_dir
    )
    return ProjectRegistry()


@pytest.fixture
def sample_projects(tmp_path):
    """Create sample project directories."""
    projects = {}

    # Create project with git
    proj1 = tmp_path / "project1"
    proj1.mkdir()
    (proj1 / ".git").mkdir()
    (proj1 / "codemcp.toml").touch()
    projects["project1"] = proj1

    # Create project without git
    proj2 = tmp_path / "project2"
    proj2.mkdir()
    (proj2 / "codemcp.toml").touch()
    projects["project2"] = proj2

    return projects


@pytest.mark.asyncio
async def test_ensure_initialized(registry, temp_config_dir):
    """Test that registry initialization creates necessary files and directories."""
    await registry.ensure_initialized()

    assert registry.registry_path.exists()
    assert registry.workspace_dir.exists()

    # Check default config content
    with open(registry.registry_path, "r") as f:
        config = toml.load(f)
        assert config == {"projects": {}}


@pytest.mark.asyncio
async def test_register_project(registry, sample_projects):
    """Test registering a new project."""
    proj_path = sample_projects["project1"]

    await registry.register_project("test-proj", str(proj_path))

    # Check registry file
    projects = await registry.load_projects()
    assert "test-proj" in projects
    assert projects["test-proj"] == str(proj_path)

    # Check symlink
    symlink = registry.workspace_dir / "test-proj"
    assert symlink.is_symlink()
    assert symlink.resolve() == proj_path.resolve()


@pytest.mark.asyncio
async def test_register_nonexistent_path(registry):
    """Test registering a project with non-existent path raises error."""
    with pytest.raises(ValueError, match="does not exist"):
        await registry.register_project("bad-proj", "/nonexistent/path")


@pytest.mark.asyncio
async def test_unregister_project(registry, sample_projects):
    """Test unregistering a project."""
    proj_path = sample_projects["project1"]

    # First register
    await registry.register_project("test-proj", str(proj_path))

    # Then unregister
    await registry.unregister_project("test-proj")

    # Check it's gone from registry
    projects = await registry.load_projects()
    assert "test-proj" not in projects

    # Check symlink is removed
    symlink = registry.workspace_dir / "test-proj"
    assert not symlink.exists()


@pytest.mark.asyncio
async def test_unregister_nonexistent_project(registry):
    """Test unregistering non-existent project raises error."""
    with pytest.raises(ValueError, match="not found in registry"):
        await registry.unregister_project("nonexistent")


@pytest.mark.asyncio
async def test_get_project_for_path(registry, sample_projects):
    """Test finding which project contains a given path."""
    proj1 = sample_projects["project1"]
    proj2 = sample_projects["project2"]

    await registry.register_project("proj1", str(proj1))
    await registry.register_project("proj2", str(proj2))

    # Test exact project paths
    assert await registry.get_project_for_path(str(proj1)) == "proj1"
    assert await registry.get_project_for_path(str(proj2)) == "proj2"

    # Test subpaths
    subdir = proj1 / "src" / "components"
    subdir.mkdir(parents=True)
    assert await registry.get_project_for_path(str(subdir)) == "proj1"

    # Test path outside any project
    assert await registry.get_project_for_path("/tmp") is None


@pytest.mark.asyncio
async def test_list_projects(registry, sample_projects):
    """Test listing all projects with status."""
    proj1 = sample_projects["project1"]
    proj2 = sample_projects["project2"]

    await registry.register_project("proj1", str(proj1))
    await registry.register_project("proj2", str(proj2))

    projects = await registry.list_projects()

    assert len(projects) == 2

    # Find projects in list
    proj1_info = next(p for p in projects if p["name"] == "proj1")
    proj2_info = next(p for p in projects if p["name"] == "proj2")

    # Check proj1 (has git)
    assert proj1_info["exists"] is True
    assert proj1_info["is_git"] is True
    assert proj1_info["symlink_ok"] is True

    # Check proj2 (no git)
    assert proj2_info["exists"] is True
    assert proj2_info["is_git"] is False
    assert proj2_info["symlink_ok"] is True


@pytest.mark.asyncio
async def test_sync_workspace(registry, sample_projects):
    """Test syncing workspace removes orphaned symlinks and creates missing ones."""
    proj1 = sample_projects["project1"]

    # Create an orphaned symlink
    orphan = registry.workspace_dir / "orphan"
    orphan.symlink_to("/nonexistent")

    # Register a project
    await registry.register_project("proj1", str(proj1))

    # Remove the symlink manually
    (registry.workspace_dir / "proj1").unlink()

    # Sync workspace
    await registry.sync_workspace()

    # Check orphan is removed
    assert not orphan.exists()

    # Check proj1 symlink is recreated
    symlink = registry.workspace_dir / "proj1"
    assert symlink.is_symlink()
    assert symlink.resolve() == proj1.resolve()


@pytest.mark.asyncio
async def test_cache_behavior(registry, sample_projects):
    """Test that the registry caches loaded projects."""
    proj1 = sample_projects["project1"]

    # Register a project
    await registry.register_project("proj1", str(proj1))

    # Load projects (should cache)
    projects1 = await registry.load_projects()

    # Modify the file directly
    config = {"projects": {"proj1": str(proj1), "proj2": "/fake/path"}}
    with open(registry.registry_path, "w") as f:
        toml.dump(config, f)

    # Load again (should return cached value)
    projects2 = await registry.load_projects()
    assert projects2 == projects1
    assert "proj2" not in projects2

    # Clear cache by registering new project
    await registry.register_project("proj3", str(sample_projects["project2"]))

    # Now it should reload
    projects3 = await registry.load_projects()
    assert "proj2" in projects3
    assert "proj3" in projects3
