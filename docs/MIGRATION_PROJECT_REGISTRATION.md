# Migration Guide: Moving to Project Registration

If you're currently using codemcp with all projects under `~/projects`, here's how to migrate to the new project registration system.

## Benefits of Migration

- **Flexible project locations**: Keep projects anywhere on your filesystem
- **Explicit control**: Only indexed projects are those you explicitly register
- **Better organization**: Logical project names instead of filesystem paths
- **Network mount support**: Register projects from network drives or external storage

## Migration Steps

### 1. List Your Current Projects

First, see what projects you have in `~/projects`:

```bash
ls -la ~/projects/
```

### 2. Register Each Project

For each project, register it with a logical name:

```bash
# Register projects that are already in ~/projects
codemcp project register webapp ~/projects/my-web-app
codemcp project register backend ~/projects/api-server
codemcp project register tools ~/projects/dev-tools

# You can also register projects from other locations now
codemcp project register archive /mnt/backup/old-projects/legacy-app
codemcp project register experiment ~/Documents/research/ml-experiment
```

### 3. Update Docker Compose

Edit `docker/opengrok/docker-compose.yml` to use the new workspace:

```yaml
services:
  opengrok:
    volumes:
      # OLD:
      # - ${OPENGROK_WORKSPACE:-~/projects}:/opengrok/src:ro
      # NEW:
      - ~/.codemcp/opengrok-workspace:/opengrok/src:ro
```

### 4. Restart OpenGrok

```bash
cd docker/opengrok
docker-compose down
docker-compose up -d
```

### 5. Verify Setup

Check that everything is working:

```bash
# List registered projects
codemcp project list

# Check which project you're in
cd ~/projects/my-web-app
codemcp project which

# Verify OpenGrok can search
# In Claude, use opengrok_search and it should automatically scope to your project
```

## Keeping the Old Setup

If you prefer to keep using `~/projects` without registration:

1. Don't register any projects
2. Keep docker-compose.yml unchanged
3. OpenGrok will continue to work as before

The project registration system is **optional** - the old approach still works!

## Rollback

If you want to go back to the old approach:

1. Update docker-compose.yml back to the original mount:
   ```yaml
   - ${OPENGROK_WORKSPACE:-~/projects}:/opengrok/src:ro
   ```

2. Restart OpenGrok

3. Remove the project registry (optional):
   ```bash
   rm -rf ~/.codemcp/projects.toml
   rm -rf ~/.codemcp/opengrok-workspace
   ```
