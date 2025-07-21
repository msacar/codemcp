#!/usr/bin/env python3
"""End-to-end tests for project CLI commands."""

import subprocess
import tempfile
from pathlib import Path

import pytest
import toml


def run_codemcp_command(args, cwd=None):
    """Run a codemcp command and return the result."""
    cmd = ["python", "-m", "codemcp"] + args
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


@pytest.fixture
def temp_home(monkeypatch):
    """Create a temporary home directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        yield Path(tmpdir)


@pytest.fixture
def sample_projects(tmp_path):
    """Create sample project directories."""
    projects = {}

    # Create project with git
    proj1 = tmp_path / "project1"
    proj1.mkdir()
    subprocess.run(["git", "init"], cwd=proj1, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=proj1, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=proj1, check=True
    )
    (proj1 / "codemcp.toml").write_text("[commands]\ntest = ['echo', 'test']")
    subprocess.run(["git", "add", "."], cwd=proj1, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=proj1, check=True)
    projects["project1"] = proj1

    # Create project without git
    proj2 = tmp_path / "project2"
    proj2.mkdir()
    (proj2 / "codemcp.toml").touch()
    projects["project2"] = proj2

    return projects


def test_project_register(temp_home, sample_projects):
    """Test registering a project via CLI."""
    proj_path = sample_projects["project1"]

    # Register project
    result = run_codemcp_command(["project", "register", "test-proj", str(proj_path)])

    assert result.returncode == 0
    assert "Successfully registered project 'test-proj'" in result.stdout

    # Check registry file was created
    registry_file = temp_home / ".codemcp" / "projects.toml"
    assert registry_file.exists()

    # Check content
    with open(registry_file, "r") as f:
        config = toml.load(f)
        assert config["projects"]["test-proj"] == str(proj_path)


def test_project_list(temp_home, sample_projects):
    """Test listing projects via CLI."""
    # Register two projects
    run_codemcp_command(
        ["project", "register", "proj1", str(sample_projects["project1"])]
    )
    run_codemcp_command(
        ["project", "register", "proj2", str(sample_projects["project2"])]
    )

    # List projects
    result = run_codemcp_command(["project", "list"])

    assert result.returncode == 0
    assert "proj1" in result.stdout
    assert "proj2" in result.stdout
    assert "✅ OK" in result.stdout  # Status should be OK
    assert "OpenGrok workspace:" in result.stdout


def test_project_unregister(temp_home, sample_projects):
    """Test unregistering a project via CLI."""
    proj_path = sample_projects["project1"]

    # Register then unregister
    run_codemcp_command(["project", "register", "test-proj", str(proj_path)])
    result = run_codemcp_command(["project", "unregister", "test-proj"])

    assert result.returncode == 0
    assert "Successfully unregistered project 'test-proj'" in result.stdout

    # Verify it's gone
    list_result = run_codemcp_command(["project", "list"])
    assert "test-proj" not in list_result.stdout


def test_project_which(temp_home, sample_projects):
    """Test finding which project contains a path."""
    proj_path = sample_projects["project1"]
    subdir = proj_path / "src"
    subdir.mkdir()

    # Register project
    run_codemcp_command(["project", "register", "myproject", str(proj_path)])

    # Check which project contains the subdirectory
    result = run_codemcp_command(["project", "which", str(subdir)])

    assert result.returncode == 0
    assert "Path belongs to project: myproject" in result.stdout
    assert f"Project root: {proj_path}" in result.stdout


def test_project_which_not_registered(temp_home, sample_projects):
    """Test 'which' command for unregistered path."""
    result = run_codemcp_command(["project", "which", str(sample_projects["project1"])])

    assert result.returncode == 0
    assert "Path is not within any registered project" in result.stdout


def test_project_sync(temp_home, sample_projects):
    """Test syncing workspace symlinks."""
    # Register a project
    run_codemcp_command(
        ["project", "register", "proj1", str(sample_projects["project1"])]
    )

    # Manually remove the symlink
    workspace_dir = temp_home / ".codemcp" / "opengrok-workspace"
    symlink = workspace_dir / "proj1"
    if symlink.exists():
        symlink.unlink()

    # Run sync
    result = run_codemcp_command(["project", "sync"])

    assert result.returncode == 0
    assert "Synced 1/1 projects" in result.stdout

    # Check symlink was recreated
    assert symlink.is_symlink()


def test_project_register_nonexistent_path(temp_home):
    """Test registering with non-existent path fails."""
    result = run_codemcp_command(["project", "register", "bad", "/nonexistent/path"])

    assert result.returncode != 0
    assert "Failed to register project" in result.stderr


def test_project_list_empty(temp_home):
    """Test listing when no projects are registered."""
    result = run_codemcp_command(["project", "list"])

    assert result.returncode == 0
    assert "No projects registered yet" in result.stdout
    assert "Use 'codemcp project register" in result.stdout
