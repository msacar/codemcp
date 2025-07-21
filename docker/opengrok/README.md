# OpenGrok Docker Setup for Codemcp

This directory contains the Docker configuration for running OpenGrok as a code search service for codemcp.

## Quick Start

1. Start OpenGrok:
```bash
cd docker/opengrok
docker-compose up -d
```

2. Wait for initial indexing (check logs):
```bash
docker-compose logs -f opengrok
```

3. Access OpenGrok web UI:
- URL: http://localhost:8080/source
- API: http://localhost:8080/source/api/v1/

## Configuration

### Environment Variables

- `PROJECT_PATH`: Path to the project to index (default: `../..` - the codemcp root)
- `REINDEX`: Re-indexing interval in seconds (default: 600)
- `INDEXER_THREADS`: Number of indexing threads (default: 4)
- `JAVA_OPTS`: JVM options (default: `-Xmx2g -Xms512m`)

### Custom Project Path

To index a different project:
```bash
PROJECT_PATH=/path/to/your/project docker-compose up -d
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
