# OpenGrok Docker Setup for Codemcp

This directory contains the Docker configuration for running OpenGrok as a code search service for codemcp.

## Quick Start

1. **Prepare your workspace** (OpenGrok will index all Git projects in this directory):
   ```bash
   mkdir -p ~/projects
   # Move or clone your projects into ~/projects
   ```

2. **Start OpenGrok**:
   ```bash
   cd docker/opengrok
   docker-compose up -d
   ```

   Or to specify a custom workspace:
   ```bash
   OPENGROK_WORKSPACE=/path/to/workspace docker-compose up -d
   ```

3. **Wait for initial indexing** (check logs):
   ```bash
   docker-compose logs -f opengrok
   ```

4. **Access OpenGrok web UI**:
   - URL: http://localhost:8080/source
   - API: http://localhost:8080/source/api/v1/

## Multi-Project Support

OpenGrok automatically detects and indexes all Git repositories in the workspace directory. Each project:
- Is indexed separately
- Can be searched individually or together
- Appears as a separate project in the web UI

When using codemcp tools, the project is automatically detected based on the current working directory.

## Configuration

### Environment Variables

- `OPENGROK_WORKSPACE`: Path to workspace containing multiple projects (default: `~/projects`)
- `REINDEX`: Re-indexing interval in seconds (default: 600)
- `INDEXER_THREADS`: Number of indexing threads (default: 4)
- `JAVA_OPTS`: JVM options (default: `-Xmx2g -Xms512m`)

### Workspace Structure

```
~/projects/                  # OPENGROK_WORKSPACE
├── project1/               # Auto-detected as "project1"
│   ├── .git/
│   └── codemcp.toml
├── project2/               # Auto-detected as "project2"
│   ├── .git/
│   └── codemcp.toml
└── project3/               # Auto-detected as "project3"
    ├── .git/
    └── codemcp.toml
```

## Management Commands

### Stop OpenGrok
```bash
docker-compose down
```

### Clean all data and re-index
```bash
docker-compose down -v
docker-compose up -d
```

### View logs
```bash
docker-compose logs -f opengrok
```

### Check health status
```bash
docker-compose ps
```

## API Usage

OpenGrok provides a REST API for searching:

```bash
# Search for a term
curl "http://localhost:8080/source/api/v1/search?q=function&projects=src"

# Get suggestions
curl "http://localhost:8080/source/api/v1/suggest?q=test"

# Get file content
curl "http://localhost:8080/source/api/v1/file?path=/path/to/file"
```

## Troubleshooting

1. **Container won't start**: Check if port 8080 is already in use
2. **Indexing takes too long**: Reduce `INDEXER_THREADS` or increase memory
3. **Search not working**: Wait for initial indexing to complete
4. **Out of memory**: Increase `JAVA_OPTS` memory settings

## Integration with Codemcp

The `opengrok_search` tool in codemcp automatically uses this OpenGrok instance when available.
