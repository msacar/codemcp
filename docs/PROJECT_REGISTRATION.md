# Project Registration System

## Overview

The codemcp project registration system allows you to work with projects located anywhere on your filesystem, not just under a common workspace directory. This is achieved through an explicit project registry that maps logical project names to filesystem paths.

## How It Works

1. **Project Registry**: A configuration file (`~/.codemcp/projects.toml`) maintains mappings between project names and their filesystem paths.

2. **Direct Docker Mounts**: Each registered project must be manually added to `docker-compose.yml` as a bind mount. This gives OpenGrok direct access to index projects from any location.

3. **Automatic Project Detection**: When you use OpenGrok search tools, the system first checks if your current path belongs to a registered project, then falls back to Git-based detection.

## Quick Start

### 1. Register a Project

```bash
# Register a project at any filesystem location
codemcp project register myapp /Users/me/work/myapp
```

This will output instructions like:
```
✅ Successfully registered project 'myapp' -> /Users/me/work/myapp

To complete the setup, add this line to docker/opengrok/docker-compose.yml:

      - /Users/me/work/myapp:/opengrok/src/myapp:ro

Add it under the 'volumes:' section, then restart OpenGrok:
  cd ~/codemcp/docker/opengrok
  docker-compose down
  docker-compose up -d
```

### 2. Update docker-compose.yml

Add the mount line to your `docker-compose.yml`:

```yaml
services:
  opengrok:
    volumes:
      - /Users/me/work/myapp:/opengrok/src/myapp:ro
      - /home/me/projects/backend:/opengrok/src/backend:ro
      # Add more projects as needed
      - opengrok-data:/opengrok/data
```

### 3. List Registered Projects

```bash
codemcp project list
```

Output:
```
Registered Projects:
+----------+--------------------------------+--------+-----+
| Name     | Path                           | Status | Git |
+==========+================================+========+=====+
| myapp    | /Users/me/work/myapp          | ✅ OK  | ✅  |
| backend  | /home/me/projects/backend-api | ✅ OK  | ✅  |
| tools    | /mnt/shared/dev-tools         | ✅ OK  | ⚠️  |
+----------+--------------------------------+--------+-----+

Remember to add these projects to docker/opengrok/docker-compose.yml
See 'codemcp project register' output for details.
```

### 4. Check Which Project You're In

```bash
# From any directory within a project
cd /Users/me/work/myapp/src/components
codemcp project which

# Output:
# 📁 Path belongs to project: myapp
#    Project root: /Users/me/work/myapp
```


## Commands

### `codemcp project register <name> <path>`
Register a new project or update an existing one.

### `codemcp project unregister <name>`
Remove a project from the registry.

### `codemcp project list`
Show all registered projects with their status.

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

3. **Add to docker-compose.yml** following the instructions shown:
   ```yaml
   - ~/Documents/newproject:/opengrok/src/newproject:ro
   ```

4. **Restart OpenGrok**:
   ```bash
   cd ~/codemcp/docker/opengrok
   docker-compose down
   docker-compose up -d
   ```

5. **Work normally** - OpenGrok searches will automatically scope to your project:
   ```bash
   cd ~/Documents/newproject
   # Claude's searches will now be filtered to 'newproject'
   ```

## Benefits

- **Flexible Project Locations**: Projects can be anywhere - different drives, network mounts, user directories
- **Explicit Control**: No automatic discovery surprises, you control what's indexed
- **Transparent Configuration**: All mounted projects visible in docker-compose.yml
- **Backward Compatible**: Existing Git-based detection still works for unregistered projects
- **Reliable**: Direct Docker mounts avoid symlink resolution issues

## Troubleshooting

### Project Not Found in Searches

If OpenGrok isn't finding your project:

1. **Check docker-compose.yml** - ensure the project mount is added:
   ```yaml
   - /path/to/project:/opengrok/src/project-name:ro
   ```

2. **Restart OpenGrok** after adding mounts:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. **Wait for indexing** - check logs:
   ```bash
   docker logs -f codemcp-opengrok | grep -i index
   ```

### Project Path Changed

If you moved a project to a new location:

1. Update the registration:
   ```bash
   codemcp project register myapp /new/path/to/myapp
   ```

2. Update the mount in docker-compose.yml:
   ```yaml
   # Change from:
   - /old/path/to/myapp:/opengrok/src/myapp:ro
   # To:
   - /new/path/to/myapp:/opengrok/src/myapp:ro
   ```

3. Restart OpenGrok

### Docker Permission Issues

If Docker can't access your project files:

1. Check Docker Desktop file sharing settings
2. Ensure parent directories are included in allowed paths
3. Try using absolute paths in docker-compose.yml

### Generate Mount Lines

To generate mount lines for all registered projects:
```bash
./scripts/generate_docker_mounts.py
```

## Implementation Details

- Project names must be valid directory names (no special characters)
- Each project requires a corresponding mount in docker-compose.yml
- The registry uses TOML format for easy manual editing if needed
- Project detection order: Registry → Git repository name → None
