# Project Registration - Installation Fix

## The Issue
When running `uvx --from /Users/mustafaacar/codemcp codemcp serve`, you got:
```
ModuleNotFoundError: No module named 'tabulate'
```

This happened because the project registration feature added new dependencies that weren't installed in your cached environment.

## The Fix

### Option 1: Force Reinstall (Recommended)
```bash
# For local directory
uvx --reinstall --python 3.12 --from /Users/mustafaacar/codemcp codemcp serve

# For GitHub
uvx --reinstall --from git+https://github.com/ezyang/codemcp@main codemcp serve
```

### Option 2: Local Development Install
```bash
cd /Users/mustafaacar/codemcp
uv venv
source .venv/bin/activate  # or .venv/bin/activate.fish for fish shell
uv pip install -e ".[dev]"
python -m codemcp serve
```

### Option 3: Direct Run
```bash
cd /Users/mustafaacar/codemcp
uv run python -m codemcp serve
```

## Verify It Works
After installation, test the new project commands:
```bash
# Check help
python -m codemcp project --help

# Register a project
python -m codemcp project register myapp /path/to/myapp

# List projects
python -m codemcp project list
```

## What Changed
1. Added dependencies:
   - `tabulate>=0.9.0` - For formatting project lists
   - `aiofiles>=0.12.0` - For async file operations

2. Fixed import path in `cli/project.py`:
   - Changed from `.project_registry` to `..project_registry`

3. Updated `docker-compose.yml` to use:
   - `~/.codemcp/opengrok-workspace:/opengrok/src:ro`

## Why This Happened
The `uvx` tool caches installations, so when new dependencies are added, you need to either:
- Force a reinstall with `--reinstall`
- Clear the cache manually
- Use a local development installation

The project registration system is now fully functional and ready to use!
