# OpenGrok Integration for codemcp

OpenGrok provides powerful code search capabilities for codemcp projects.

## Setup

### 1. Register your projects

```bash
# Register projects you want to index
codemcp project register myapp /path/to/myapp
codemcp project register backend /path/to/backend

# List registered projects
codemcp project list
```

### 2. Update docker-compose.yml

After registering projects, you need to add them to `docker-compose.yml`:

```bash
# Generate mount entries for all registered projects
./scripts/generate_docker_mounts.py

# Manually add the output to docker-compose.yml under volumes:
```

Example docker-compose.yml volumes section:
```yaml
volumes:
  - /Users/mustafa/projects/myapp:/opengrok/src/myapp:ro
  - /Users/mustafa/projects/backend:/opengrok/src/backend:ro
  # Add more projects as needed
  - opengrok-data:/opengrok/data
```

### 3. Start OpenGrok

```bash
# From this directory
docker-compose up -d

# Or use the helper script for a fresh start
../../scripts/restart_opengrok.sh
```

## Usage

### Web Interface
- Browse to http://localhost:8080/source
- Search across all indexed projects
- Use project dropdown to filter by project

### API Access (used by codemcp)
- Search: `curl "http://localhost:8080/source/api/v1/search?q=TODO&project=myapp"`
- Ping: `curl http://localhost:8080/source/api/v1/system/ping`

## Adding New Projects

1. Register the project: `codemcp project register newproject /path/to/newproject`
2. Add to docker-compose.yml: `- /path/to/newproject:/opengrok/src/newproject:ro`
3. Restart OpenGrok: `docker-compose restart`

## Troubleshooting

### "Index database not found"
The index is being built. Check progress:
```bash
docker logs -f codemcp-opengrok
```

### Projects not appearing
1. Ensure the path is added to docker-compose.yml
2. Restart OpenGrok: `docker-compose down && docker-compose up -d`
3. Wait for indexing to complete

### Docker permission issues
Ensure Docker Desktop has access to your project directories:
- Docker Desktop → Settings → Resources → File Sharing
- Add parent directories of your projects

## Configuration

- Re-index interval: 10 minutes (configured in docker-compose.yml)
- Memory: 2GB max, 512MB initial
- Indexer threads: 4
- Only Git-tracked files are indexed
