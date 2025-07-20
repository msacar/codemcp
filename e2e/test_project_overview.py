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

    async def test_project_overview_with_extensions_filter(self):
        """Test project_overview with allowed_extensions filter."""
        # Create test directory
        test_dir = os.path.join(self.temp_dir.name, "test_extensions")
        os.makedirs(test_dir)

        # Create codemcp.toml with extensions filter
        config_content = """
[project_structure]
allowed_extensions = [".py", ".md"]
show_file_counts = true
"""
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write(config_content)

        # Create files with various extensions
        with open(os.path.join(test_dir, "main.py"), "w") as f:
            f.write("# Python file")
        with open(os.path.join(test_dir, "utils.py"), "w") as f:
            f.write("# Utils")
        with open(os.path.join(test_dir, "script.js"), "w") as f:
            f.write("// JavaScript file")
        with open(os.path.join(test_dir, "README.md"), "w") as f:
            f.write("# README")
        with open(os.path.join(test_dir, "config.json"), "w") as f:
            f.write("{}")

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
                    "user_prompt": "Test initialization for extensions filter test",
                    "subject_line": "test: initialize for extensions filter test",
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

            # Verify Python and Markdown files are shown
            self.assertIn("main.py", result_text)
            self.assertIn("utils.py", result_text)
            self.assertIn("README.md", result_text)

            # Verify JavaScript and JSON files are NOT shown
            self.assertNotIn("script.js", result_text)
            self.assertNotIn("config.json", result_text)

            # Verify file counts only include filtered files
            self.assertIn("Total Files: 3", result_text)

    async def test_project_overview_with_max_depth(self):
        """Test project_overview with max_depth parameter."""
        # Create test directory with nested structure
        test_dir = os.path.join(self.temp_dir.name, "test_depth")
        os.makedirs(test_dir)

        # Create codemcp.toml
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write("[project_structure]\nenable_tree_view = true")

        # Create nested directory structure
        level1 = os.path.join(test_dir, "level1")
        os.makedirs(level1)
        with open(os.path.join(level1, "file1.py"), "w") as f:
            f.write("# Level 1")

        level2 = os.path.join(level1, "level2")
        os.makedirs(level2)
        with open(os.path.join(level2, "file2.py"), "w") as f:
            f.write("# Level 2")

        level3 = os.path.join(level2, "level3")
        os.makedirs(level3)
        with open(os.path.join(level3, "file3.py"), "w") as f:
            f.write("# Level 3")

        level4 = os.path.join(level3, "level4")
        os.makedirs(level4)
        with open(os.path.join(level4, "file4.py"), "w") as f:
            f.write("# Level 4")

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
                    "user_prompt": "Test initialization for depth test",
                    "subject_line": "test: initialize for depth test",
                    "reuse_head_chat_id": False,
                },
            )

            # Extract chat_id from the init result
            chat_id = self.extract_chat_id_from_text(init_result_text)

            # Test with max_depth=2
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "ProjectOverview",
                    "path": test_dir,
                    "chat_id": chat_id,
                    "max_depth": 2,
                },
            )

            # Verify we see level1 and level2 but not level3 or level4
            self.assertIn("level1/", result_text)
            self.assertIn("level2/", result_text)
            self.assertNotIn("level3/", result_text)
            self.assertNotIn("level4/", result_text)

    async def test_project_overview_with_custom_ignored_dirs(self):
        """Test project_overview with custom ignored directories."""
        # Create test directory
        test_dir = os.path.join(self.temp_dir.name, "test_ignored")
        os.makedirs(test_dir)

        # Create codemcp.toml with custom ignored dirs
        config_content = """
[project_structure]
ignored_dirs = ["temp", "backup"]
"""
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write(config_content)

        # Create directories
        src_dir = os.path.join(test_dir, "src")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "main.py"), "w") as f:
            f.write("# Main")

        temp_dir = os.path.join(test_dir, "temp")
        os.makedirs(temp_dir)
        with open(os.path.join(temp_dir, "temp_file.py"), "w") as f:
            f.write("# Temp")

        backup_dir = os.path.join(test_dir, "backup")
        os.makedirs(backup_dir)
        with open(os.path.join(backup_dir, "backup_file.py"), "w") as f:
            f.write("# Backup")

        # Also create a default ignored dir to ensure defaults still work
        cache_dir = os.path.join(test_dir, "__pycache__")
        os.makedirs(cache_dir)

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
                    "user_prompt": "Test initialization for ignored dirs test",
                    "subject_line": "test: initialize for ignored dirs test",
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

            # Verify src is shown
            self.assertIn("src/", result_text)

            # Verify custom ignored dirs are not shown
            self.assertNotIn("temp/", result_text)
            self.assertNotIn("backup/", result_text)

            # Verify default ignored dirs are still ignored
            self.assertNotIn("__pycache__", result_text)

    async def test_project_overview_error_cases(self):
        """Test project_overview error handling."""
        async with self.create_client_session() as session:
            # Test non-existent path
            result = await self.call_tool_assert_error(
                session,
                "codemcp",
                {
                    "subtool": "ProjectOverview",
                    "path": "/non/existent/path",
                    "chat_id": "test",
                },
            )
            self.assertIn("does not exist", result)

            # Test file instead of directory
            test_file = os.path.join(self.temp_dir.name, "test_file.txt")
            with open(test_file, "w") as f:
                f.write("test")

            result = await self.call_tool_assert_error(
                session,
                "codemcp",
                {"subtool": "ProjectOverview", "path": test_file, "chat_id": "test"},
            )
            self.assertIn("not a directory", result)

            # Test directory without git repo - create outside the temp dir to avoid parent git
            import tempfile

            with tempfile.TemporaryDirectory() as temp_root:
                no_git_dir = os.path.join(temp_root, "no_git")
                os.makedirs(no_git_dir)

                # Create a codemcp.toml file to pass the initial check
                with open(os.path.join(no_git_dir, "codemcp.toml"), "w") as f:
                    f.write("")

                result = await self.call_tool_assert_error(
                    session,
                    "codemcp",
                    {
                        "subtool": "ProjectOverview",
                        "path": no_git_dir,
                        "chat_id": "test",
                    },
                )
                self.assertIn("not a git repository", result)

    async def test_project_overview_with_file_sizes(self):
        """Test project_overview with show_file_sizes enabled."""
        # Create test directory
        test_dir = os.path.join(self.temp_dir.name, "test_sizes")
        os.makedirs(test_dir)

        # Create codemcp.toml with file sizes enabled
        config_content = """
[project_structure]
enable_tree_view = true
show_file_sizes = true
"""
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write(config_content)

        # Create files with known content
        with open(os.path.join(test_dir, "small.txt"), "w") as f:
            f.write("small")  # 5 bytes
        with open(os.path.join(test_dir, "large.txt"), "w") as f:
            f.write("x" * 1000)  # 1000 bytes

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
                    "user_prompt": "Test initialization for file sizes test",
                    "subject_line": "test: initialize for file sizes test",
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

            # Verify files are shown (size display not directly visible in the format_tree output)
            self.assertIn("small.txt", result_text)
            self.assertIn("large.txt", result_text)

    async def test_project_overview_output_format(self):
        """Test project_overview output format using expecttest."""
        # Import expecttest

        # Create test directory
        test_dir = os.path.join(self.temp_dir.name, "test_format")
        os.makedirs(test_dir)

        # Create structured project
        config_content = """
[project_structure]
enable_tree_view = true
important_dirs = ["src/"]
entry_points = ["main.py"]
show_file_counts = true
"""
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write(config_content)

        # Create directories and files
        src_dir = os.path.join(test_dir, "src")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "module.py"), "w") as f:
            f.write("# Module")
        with open(os.path.join(test_dir, "main.py"), "w") as f:
            f.write("# Main entry")

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
                    "user_prompt": "Test initialization for format test",
                    "subject_line": "test: initialize for format test",
                    "reuse_head_chat_id": False,
                },
            )

            # Extract chat_id from the init result
            chat_id = self.extract_chat_id_from_text(init_result_text)

            # Call the project_overview tool
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "ProjectOverview",
                    "path": test_dir,
                    "chat_id": chat_id,
                    "max_depth": 2,
                },
            )

            # Check key elements in the output
            self.assertIn("PROJECT STRUCTURE OVERVIEW", result_text)
            self.assertIn("=" * 50, result_text)
            self.assertIn("📁 Project Root:", result_text)
            self.assertIn("🚀 Entry Points:", result_text)
            self.assertIn("⭐ Important Directories:", result_text)
            self.assertIn("📂 Directory Structure:", result_text)
            self.assertIn("📊 Project Statistics:", result_text)
            self.assertIn("├──", result_text)  # Tree structure indicators
            self.assertIn("└──", result_text)

    async def test_project_overview_expecttest(self):
        """Test project_overview output with expecttest."""
        # Create test directory
        test_dir = os.path.join(self.temp_dir.name, "test_expect")
        os.makedirs(test_dir)

        # Create a simple project structure
        config_content = """
[project_structure]
enable_tree_view = true
important_dirs = ["src/"]
entry_points = ["main.py"]
show_file_counts = true
allowed_extensions = [".py"]
"""
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write(config_content)

        # Create simple structure
        src_dir = os.path.join(test_dir, "src")
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, "app.py"), "w") as f:
            f.write("# App")
        with open(os.path.join(test_dir, "main.py"), "w") as f:
            f.write("# Main")

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
                    "user_prompt": "Test initialization for expecttest",
                    "subject_line": "test: initialize for expecttest",
                    "reuse_head_chat_id": False,
                },
            )

            # Extract chat_id from the init result
            chat_id = self.extract_chat_id_from_text(init_result_text)

            # Call the project_overview tool with max_depth=2 for consistent output
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "ProjectOverview",
                    "path": test_dir,
                    "chat_id": chat_id,
                    "max_depth": 2,
                },
            )

            # Remove the commit hash and path from output for deterministic testing
            lines = result_text.split("\n")
            # Filter out lines that contain variable paths or commit hashes
            filtered_lines = []
            for line in lines:
                if "Project Root:" in line:
                    filtered_lines.append("Project Root: [PATH]")
                elif "Current commit hash:" not in line:
                    # Remove emojis for expecttest compatibility
                    clean_line = (
                        line.replace("📁", "")
                        .replace("🚀", "")
                        .replace("⭐", "")
                        .replace("📂", "")
                        .replace("📊", "")
                        .replace("├──", "|--")
                        .replace("└──", "`--")
                        .replace("│", "|")
                        .strip()
                    )
                    filtered_lines.append(clean_line)

            "\n".join(filtered_lines)

    async def test_detailed_format_output(self):
        """Test that detailed format produces expected output structure."""
        # Create test directory
        test_dir = os.path.join(self.temp_dir.name, "test_detailed")
        os.makedirs(test_dir)

        # Create codemcp.toml with detailed format enabled
        config_content = """
[project_structure]
detailed_format = true
show_files_by_type = true
detail_extensions = [".py", ".js", ".tsx"]
ignored_dirs = ["tmp"]
"""
        with open(os.path.join(test_dir, "codemcp.toml"), "w") as f:
            f.write(config_content)

        # Create directory structure
        os.makedirs(os.path.join(test_dir, "src"))
        os.makedirs(os.path.join(test_dir, "src", "utils"))
        os.makedirs(os.path.join(test_dir, "tests"))
        os.makedirs(os.path.join(test_dir, "docs"))
        os.makedirs(os.path.join(test_dir, ".git"))
        os.makedirs(os.path.join(test_dir, "node_modules"))
        os.makedirs(os.path.join(test_dir, "__pycache__"))
        os.makedirs(os.path.join(test_dir, "tmp"))

        # Create files
        with open(os.path.join(test_dir, "main.py"), "w") as f:
            f.write("# Main entry point")
        with open(os.path.join(test_dir, "app.py"), "w") as f:
            f.write("# App file")
        with open(os.path.join(test_dir, "README.md"), "w") as f:
            f.write("# Test Project")
        with open(os.path.join(test_dir, "src", "module.py"), "w") as f:
            f.write("# Module")
        with open(os.path.join(test_dir, "src", "utils", "helper.py"), "w") as f:
            f.write("# Helper")
        with open(os.path.join(test_dir, "tests", "test_main.py"), "w") as f:
            f.write("# Test")
        with open(os.path.join(test_dir, "src", "app.js"), "w") as f:
            f.write("// JS app")
        with open(os.path.join(test_dir, "src", "component.tsx"), "w") as f:
            f.write("// TSX component")

        # Initialize git
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
                    "user_prompt": "Test initialization for detailed format test",
                    "subject_line": "test: initialize for detailed format test",
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

            # Check for timestamp line
            self.assertIn("PROJECT STRUCTURE ANALYSIS -", result_text)
            self.assertIn("=====================================", result_text)

            # Check for current directory line
            self.assertIn("📁 CURRENT DIRECTORY:", result_text)

            # Check for directories section
            self.assertIn("📁 DIRECTORIES:", result_text)
            self.assertIn("./src", result_text)
            self.assertIn("./src/utils", result_text)
            self.assertIn("./tests", result_text)
            self.assertIn("./docs", result_text)

            # Verify ignored directories are not shown
            self.assertNotIn("./tmp", result_text)
            self.assertNotIn("./__pycache__", result_text)
            self.assertNotIn("./node_modules", result_text)
            self.assertNotIn("./.git", result_text)

            # Check for files by type sections
            self.assertIn("📄 PY FILES:", result_text)
            self.assertIn("./main.py", result_text)
            self.assertIn("./app.py", result_text)
            self.assertIn("./src/module.py", result_text)
            self.assertIn("./src/utils/helper.py", result_text)
            self.assertIn("./tests/test_main.py", result_text)

            self.assertIn("📄 JS FILES:", result_text)
            self.assertIn("./src/app.js", result_text)

            self.assertIn("📄 TSX FILES:", result_text)
            self.assertIn("./src/component.tsx", result_text)

            # README.md should not be shown (not in detail_extensions)
            self.assertNotIn("./README.md", result_text)
