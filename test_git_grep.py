#!/usr/bin/env python3
"""Test git grep functionality."""

import subprocess
import os
import tempfile

# Test git grep directly
with tempfile.TemporaryDirectory() as temp_dir:
    print(f"Working in: {temp_dir}")

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True
    )

    # Create test file
    test_file = os.path.join(temp_dir, "user-manager.js")
    with open(test_file, "w") as f:
        f.write("""export class UserManager {
  constructor() {
    this.users = [];
  }
}""")

    # Add and commit
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

    # Test different git grep commands
    commands = [
        ["git", "grep", "-l", "class UserManager"],
        ["git", "grep", "-li", "class UserManager"],
        ["git", "grep", "-li", "-E", "class\\s+UserManager"],
        ["git", "grep", "-li", "-E", "class\\s+UserManager", "--", "*.js"],
        ["git", "grep", "-li", "-E", "class\\s+UserManager", "--", "*.js", "*.jsx"],
    ]

    for cmd in commands:
        print(f"\nTesting command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout.strip()}")
        print(f"Stderr: {result.stderr.strip()}")
