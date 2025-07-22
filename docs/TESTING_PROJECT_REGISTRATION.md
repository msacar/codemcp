# Testing Project Registration - Step by Step Guide

> ⚠️ **Note**: This document describes testing for the original symlink-based implementation.
> The current implementation uses direct Docker bind mounts instead.
> See `OPENGROK_BIND_MOUNTS.md` for the current architecture.

This guide will help you test the new project registration feature from start to finish.

## Prerequisites

- You have `uv` installed
- You have Docker installed (for OpenGrok testing)
- You have some Git repositories to test with

## Step 1: Install/Update codemcp

### Option A: From Local Directory (Your Case)
```bash
cd /Users/mustafaacar/codemcp

# Force reinstall to get new dependencies
uvx --reinstall --python 3.12 --from . codemcp serve
```

### Option B: For Development
```bash
cd /Users/mustafaacar/codemcp
uv venv
source .venv/bin/activate  # or .venv/bin/activate.fish for fish
uv pip install -e ".[dev]"
```

## Step 2: Verify Installation

```bash
# Check if project commands are available
python -m codemcp project --help
```

You should see:
```
Usage: python -m codemcp project [OPTIONS] COMMAND [ARGS]...

  Manage codemcp project registrations.

Commands:
  list        List all registered projects.
  register    Register a project with codemcp.
  sync        Sync workspace symlinks with registered projects.
  unregister  Unregister a project from codemcp.
  which       Show which project contains the given path.
```

## Step 3: Test Basic Registration

### 3.1 Register Your First Project
```bash
# Register the codemcp project itself
codemcp project register codemcp /Users/mustafaacar/codemcp

# Register another project (use any Git repo you have)
codemcp project register myapp ~/Documents/some-project
```

Expected output:
```
✅ Successfully registered project 'codemcp' -> /Users/mustafaacar/codemcp
```

### 3.2 List Projects
```bash
codemcp project list
```

Expected output:
```
Registered Projects:
+----------+--------------------------------+--------+-----+---------+
| Name     | Path                           | Status | Git | Symlink |
+==========+================================+========+=====+=========+
| codemcp  | /Users/mustafaacar/codemcp    | ✅ OK  | ✅  | ✅      |
| myapp    | /Users/you/Documents/project  | ✅ OK  | ✅  | ✅      |
+----------+--------------------------------+--------+-----+---------+

OpenGrok workspace: /Users/mustafaacar/.codemcp/opengrok-workspace
```

### 3.3 Check Workspace Directory
```bash
# Look at the symlinks created
ls -la ~/.codemcp/opengrok-workspace/
```

You should see symlinks pointing to your actual projects:
```
codemcp -> /Users/mustafaacar/codemcp
myapp -> /Users/you/Documents/some-project
```

### 3.4 Test Project Detection
```bash
# Go to a subdirectory of a registered project
cd /Users/mustafaacar/codemcp/codemcp/tools

# Check which project you're in
codemcp project which
```

Expected output:
```
📁 Path belongs to project: codemcp
   Project root: /Users/mustafaacar/codemcp
```

### 3.5 Test with Unregistered Path
```bash
cd /tmp
codemcp project which
```

Expected output:
```
❌ Path is not within any registered project: /tmp

Registered projects:
  - codemcp: /Users/mustafaacar/codemcp
  - myapp: /Users/you/Documents/some-project
```

## Step 4: Test Project Management

### 4.1 Unregister a Project
```bash
codemcp project unregister myapp
```

Expected output:
```
✅ Successfully unregistered project 'myapp'
```

### 4.2 Test Sync Function
```bash
# Manually remove a symlink to simulate an issue
rm ~/.codemcp/opengrok-workspace/codemcp

# Run sync to fix it
codemcp project sync
```

Expected output:
```
Syncing OpenGrok workspace...
✅ Synced 1/1 projects
```

## Step 5: Test OpenGrok Integration

### 5.1 Update Docker Compose
```bash
cd /Users/mustafaacar/codemcp/docker/opengrok

# Backup original
cp docker-compose.yml docker-compose.yml.backup

# Run update script
../../scripts/update_opengrok_config.sh
```

Or manually verify the volume in `docker-compose.yml`:
```yaml
volumes:
  - ~/.codemcp/opengrok-workspace:/opengrok/src:ro
```

### 5.2 Start OpenGrok
```bash
# Stop if running
docker-compose down

# Start with new configuration
docker-compose up -d

# Watch logs
docker-compose logs -f
```

Wait for: `Indexing completed` message

### 5.3 Verify OpenGrok Web UI
Open http://localhost:8080/source

You should see your registered projects listed.

### 5.4 Test OpenGrok Search via codemcp
```bash
# Start codemcp server
cd /Users/mustafaacar/codemcp
python -m codemcp serve
```

In another terminal, create a test Python script:
```python
# test_opengrok_search.py
import asyncio
from codemcp.tools.opengrok_search import opengrok_search, check_opengrok_status

async def test():
    # Check if OpenGrok is running
    if await check_opengrok_status():
        print("✅ OpenGrok is running")

        # Search in the codemcp project
        result = await opengrok_search(
            query="project_registry",
            path="/Users/mustafaacar/codemcp",
            max_results=5
        )
        print(result)
    else:
        print("❌ OpenGrok is not running")

asyncio.run(test())
```

Run it:
```bash
python test_opengrok_search.py
```

## Step 6: Test Error Cases

### 6.1 Register Non-Existent Path
```bash
codemcp project register fake /non/existent/path
```

Expected: Error message about path not existing

### 6.2 Register Without Git (Warning)
```bash
mkdir /tmp/no-git-project
codemcp project register nogit /tmp/no-git-project
```

Expected: Warning that it's not a Git repository

### 6.3 Duplicate Registration
```bash
# Try to register same name again
codemcp project register codemcp /some/other/path
```

Expected: Updates the existing registration

## Step 7: Integration Test with Claude

1. Connect to codemcp via Claude
2. Initialize a registered project:
   ```
   Initialize codemcp for /Users/mustafaacar/codemcp
   ```

3. Test OpenGrok search:
   ```
   Use opengrok_search to find "project_registry" in the current project
   ```

4. Verify search is scoped to the correct project

## Verification Checklist

- [ ] `codemcp project --help` shows commands
- [ ] Can register projects with `codemcp project register`
- [ ] `codemcp project list` shows registered projects with status
- [ ] Symlinks created in `~/.codemcp/opengrok-workspace/`
- [ ] `codemcp project which` correctly identifies project from path
- [ ] `codemcp project sync` fixes broken symlinks
- [ ] docker-compose.yml updated to use new workspace
- [ ] OpenGrok indexes registered projects
- [ ] OpenGrok searches are scoped to current project
- [ ] Error handling works for edge cases

## Troubleshooting

### Import Errors
```bash
# Force reinstall
uvx --reinstall --python 3.12 --from /Users/mustafaacar/codemcp codemcp serve
```

### Symlink Issues
```bash
# Check symlinks
ls -la ~/.codemcp/opengrok-workspace/

# Recreate all symlinks
codemcp project sync
```

### OpenGrok Not Finding Projects
```bash
# Restart OpenGrok
cd docker/opengrok
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs opengrok
```

### Permission Issues
```bash
# Ensure directories are accessible
chmod 755 ~/.codemcp
chmod 755 ~/.codemcp/opengrok-workspace
```

## Success Indicators

1. ✅ All CLI commands work without errors
2. ✅ Projects appear in `codemcp project list`
3. ✅ Symlinks exist in workspace directory
4. ✅ OpenGrok web UI shows registered projects
5. ✅ OpenGrok searches return results from correct project
6. ✅ Claude can use the tools with proper project scoping

Congratulations! If all tests pass, the project registration system is working correctly! 🎉
