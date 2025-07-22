# OpenGrok Direct Bind Mount Implementation

## Overview

We've switched from a symlink-based approach to direct bind mounts for OpenGrok integration. This solves the Docker symlink limitation where Docker cannot follow symlinks that point outside the mounted volume.

## Architecture

### Previous Approach (Symlinks)
- Created symlinks in `~/.codemcp/opengrok-workspace/`
- Mounted the workspace directory in Docker
- **Problem**: Docker couldn't resolve symlinks pointing outside the mount

### New Approach (Direct Bind Mounts)
- Projects are registered in `~/.codemcp/projects.toml` for MCP tracking
- Each project is mounted directly in `docker-compose.yml`
- No symlinks needed - Docker has direct access to project directories

## Usage

### 1. Register a Project

```bash
codemcp project register myapp /path/to/myapp
```

This will:
- Add the project to `~/.codemcp/projects.toml`
- Display instructions for updating `docker-compose.yml`

### 2. Update docker-compose.yml

Add the mount line shown in the registration output:

```yaml
services:
  opengrok:
    volumes:
      - /path/to/myapp:/opengrok/src/myapp:ro
      # ... other projects ...
```

### 3. Restart OpenGrok

```bash
cd ~/codemcp/docker/opengrok
docker-compose down
docker-compose up -d
```

Or use the helper script:
```bash
./scripts/restart_opengrok.sh
```

## Helper Scripts

### Generate All Mounts
```bash
./scripts/generate_docker_mounts.py
```
Outputs all registered projects as docker-compose volume entries.

### Restart with Fresh Index
```bash
./scripts/restart_opengrok.sh
```
Stops OpenGrok, clears the index, and restarts with fresh indexing.

## Benefits

1. **Reliable**: No symlink resolution issues
2. **Explicit**: Clear visibility of mounted projects in docker-compose.yml
3. **Secure**: Only explicitly listed projects are accessible
4. **Simple**: Straightforward Docker volume mounts

## Migration from Symlinks

If you were using the symlink approach:

1. Remove old workspace: `rm -rf ~/.codemcp/opengrok-workspace`
2. Update docker-compose.yml with direct mounts
3. Restart OpenGrok

## Future Enhancements

Potential improvements while keeping the simple approach:

1. **Semi-automated docker-compose updates**: Script to inject mount lines
2. **Project groups**: Mount parent directories for related projects
3. **Mount validation**: Check Docker Desktop file sharing settings

## Troubleshooting

### Docker Permission Denied
Ensure Docker Desktop has file sharing enabled for your project paths:
- Docker Desktop → Settings → Resources → File Sharing
- Add project parent directories

### Index Not Found
Wait for indexing to complete after restart:
```bash
docker logs -f codemcp-opengrok | grep -i index
```
