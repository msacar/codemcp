# Project Registration System

## Overview

The codemcp project registration system allows you to work with projects located anywhere on your filesystem, not just under a common workspace directory. This is achieved through an explicit project registry that maps logical project names to filesystem paths.

## How It Works

1. **Project Registry**: A configuration file (`~/.codemcp/projects.toml`) maintains mappings between project names and their filesystem paths.

2. **Symlink Workspace**: The system automatically creates symlinks in `~/.codemcp/opengrok-workspace/` that point to your actual project directories. This allows OpenGrok to index projects from disparate locations.

3. **Automatic Project Detection**: When you use OpenGrok search tools, the system first checks if your current path belongs to a registered project, then falls back to Git-based detection.

## Quick Start

### 1. Register a Project

```bash
# Register a project at any filesystem location
codemcp project register myapp /Users/me/work/myapp
codemcp project register backend ~/projects/backend-api
codemcp project register tools /mnt/shared/dev-tools
```

### 2. List Registered Projects

```bash
codemcp project list
```

Output:
```
Registered Projects:
+----------+--------------------------------+--------+-----+---------+
| Name     | Path                           | Status | Git | Symlink |
+==========+================================+========+=====+=========+
| myapp    | /Users/me/work/myapp          | ✅ OK  | ✅  | ✅      |
| backend  | /home/me/projects/backend-api | ✅ OK  | ✅  | ✅      |
| tools    | /mnt/shared/dev-tools         | ✅ OK  | ⚠️  | ✅      |
+----------+--------------------------------+--------+-----+---------+

OpenGrok workspace: /Users/me/.codemcp/opengrok-workspace
```

### 3. Check Which Project You're In

```bash
# From any directory within a project
cd /Users/me/work/myapp/src/components
codemcp project which

# Output:
# 📁 Path belongs to project: myapp
#    Project root: /Users/me/work/myapp
```

### 4. Update Docker Compose

Update your `docker-compose.yml` to mount the managed workspace:

```yaml
services:
  opengrok:
    volumes:
      # Mount the managed workspace instead of ~/projects
      - ~/.codemcp/opengrok-workspace:/opengrok/src:ro
```

## Commands

### `codemcp project register <name> <path>`
Register a new project or update an existing one.

### `codemcp project unregister <name>`
Remove a project from the registry.

### `codemcp project list`
Show all registered projects with their status.

### `codemcp project sync`
Recreate all workspace symlinks (useful after moving projects).

### `codemcp project which [path]`
Show which project contains the given path (defaults to current directory).

## Configuration

The project registry is stored in `~/.codemcp/projects.toml`:

```toml
[projects]
myapp = "/Users/me/work/myapp"
backend = "/home/me/projects/backend-api"
tools = "/mnt/shared/dev-tools"
legacy-monolith = "/archive/old-systems/monolith"
```

## Developer Workflow

1. **Clone a new project** anywhere on your filesystem:
   ```bash
   git clone https://github.com/company/newproject ~/Documents/newproject
   ```

2. **Register it with codemcp**:
   ```bash
   codemcp project register newproject ~/Documents/newproject
   ```

3. **Work normally** - OpenGrok searches will automatically scope to your project:
   ```bash
   cd ~/Documents/newproject
   # Claude's searches will now be filtered to 'newproject'
   ```

## Benefits

- **Flexible Project Locations**: Projects can be anywhere - different drives, network mounts, user directories
- **Explicit Control**: No automatic discovery surprises, you control what's indexed
- **Fast Project Switching**: No need to restart OpenGrok when switching projects
- **Backward Compatible**: Existing Git-based detection still works for unregistered projects
- **Clean Workspace**: OpenGrok sees a clean, organized workspace regardless of your actual filesystem layout

## Troubleshooting

### Symlink Issues

If you see ❌ in the Symlink column when running `codemcp project list`, run:
```bash
codemcp project sync
```

### Project Path Changed

If you moved a project to a new location:
```bash
codemcp project register myapp /new/path/to/myapp
```

### OpenGrok Not Finding Projects

1. Ensure Docker Compose is using the managed workspace:
   ```yaml
   - ~/.codemcp/opengrok-workspace:/opengrok/src:ro
   ```

2. Restart OpenGrok after registering projects:
   ```bash
   docker-compose restart opengrok
   ```

3. Wait for indexing to complete (check OpenGrok web UI at http://localhost:8080)

## Implementation Details

- Project names must be valid directory names (no special characters)
- Symlinks are automatically managed - don't modify them directly
- The registry uses TOML format for easy manual editing if needed
- Project detection order: Registry → Git repository name → None
