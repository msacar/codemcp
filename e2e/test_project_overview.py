#!/usr/bin/env python3

"""Tests for the project_overview tool."""

import os

from codemcp.testing import MCPEndToEndTestCase


class ProjectOverviewTest(MCPEndToEndTestCase):
    """Test the project_overview tool."""

    async def test_project_overview(self):
        """Test the project_overview tool with configuration."""
        # Create test directory structure
        test_dir = os.path.join(self.temp_dir.name, "test_project")
        os.makedirs(test_dir)

        # Create codemcp.toml with project structure config
        config_content = """
[project_structure]
enable_tree_view = true
important_dirs = ["src/", "tests/"]
entry_points = ["main.py"]
show_file_counts = true
"""
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write(config_content)

        # Create test directory structure
        src_dir = os.path.join(test_dir, "src")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(src_dir, "app.py"), "w") as f:
            f.write("# Main app")
        with open(os.path.join(src_dir, "utils.py"), "w") as f:
            f.write("# Utils")

        tests_dir = os.path.join(test_dir, "tests")
        os.makedirs(tests_dir)
        with open(os.path.join(tests_dir, "test_app.py"), "w") as f:
            f.write("# Tests")

        with open(os.path.join(test_dir, "main.py"), "w") as f:
            f.write("# Entry point")
        with open(os.path.join(test_dir, "README.md"), "w") as f:
            f.write("# Test Project")

        # Create ignored directories
        os.makedirs(os.path.join(test_dir, "__pycache__"))
        os.makedirs(os.path.join(test_dir, "node_modules"))

        # Initialize git repository
        os.system(f"cd {test_dir} && git init --initial-branch=main")
        os.system(f"cd {test_dir} && git add -A && git commit -m 'Initial commit'")

        async with self.create_client_session() as session:
            # First initialize project to get chat_id
            init_result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "InitProject",
                    "path": test_dir,
                    "user_prompt": "Test initialization for project overview test",
                    "subject_line": "test: initialize for project overview test",
                    "reuse_head_chat_id": False,
                },
            )

            # Extract chat_id from the init result
            chat_id = self.extract_chat_id_from_text(init_result_text)

            # Call the project_overview tool
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {"subtool": "ProjectOverview", "path": test_dir, "chat_id": chat_id},
            )

            # Verify the output contains expected elements
            self.assertIn("PROJECT STRUCTURE OVERVIEW", result_text)
            self.assertIn("Project Root:", result_text)
            self.assertIn("Entry Points:", result_text)
            self.assertIn("main.py", result_text)
            self.assertIn("Important Directories:", result_text)
            self.assertIn("src/", result_text)
            self.assertIn("tests/", result_text)
            self.assertIn("Directory Structure:", result_text)
            self.assertIn("Project Statistics:", result_text)
            self.assertIn("Total Directories:", result_text)
            self.assertIn("Total Files:", result_text)

            # Verify ignored directories are not shown
            self.assertNotIn("__pycache__", result_text)
            self.assertNotIn("node_modules", result_text)

    async def test_project_overview_no_config(self):
        """Test project_overview with default configuration."""
        # Create test directory
        test_dir = os.path.join(self.temp_dir.name, "test_project_minimal")
        os.makedirs(test_dir)

        # Create minimal codemcp.toml
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write("")

        # Create some files
        with open(os.path.join(test_dir, "file1.py"), "w") as f:
            f.write("# File 1")
        with open(os.path.join(test_dir, "file2.js"), "w") as f:
            f.write("// File 2")

        # Initialize git repository
        os.system(f"cd {test_dir} && git init --initial-branch=main")
        os.system(f"cd {test_dir} && git add -A && git commit -m 'Initial commit'")

        async with self.create_client_session() as session:
            # First initialize project to get chat_id
            init_result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "InitProject",
                    "path": test_dir,
                    "user_prompt": "Test initialization for minimal project overview test",
                    "subject_line": "test: initialize for minimal project overview test",
                    "reuse_head_chat_id": False,
                },
            )

            # Extract chat_id from the init result
            chat_id = self.extract_chat_id_from_text(init_result_text)

            # Call the project_overview tool
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {"subtool": "ProjectOverview", "path": test_dir, "chat_id": chat_id},
            )

            # Verify basic output structure
            self.assertIn("PROJECT STRUCTURE OVERVIEW", result_text)
            self.assertIn("Project Root:", result_text)
            self.assertIn("Project Statistics:", result_text)
            self.assertIn("Total Files:", result_text)
            self.assertIn("file1.py", result_text)
            self.assertIn("file2.js", result_text)
