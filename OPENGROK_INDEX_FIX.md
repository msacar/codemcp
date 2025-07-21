# OpenGrok Index Fix

The issue you're experiencing is that OpenGrok hasn't properly indexed the new workspace after switching from `~/projects` to `~/.codemcp/opengrok-workspace`. The error message shows it's looking for index files but the index is corrupted or missing.

## Quick Fix

Run the fix script:
```bash
cd /Users/mustafaacar/codemcp
./fix_opengrok_index.sh
```

This script will:
1. Stop OpenGrok
2. Clear the old index data
3. Restart OpenGrok with fresh indexing
4. Monitor the indexing progress

## Manual Fix Steps

If you prefer to do it manually:

```bash
cd /Users/mustafaacar/codemcp/docker/opengrok

# 1. Stop OpenGrok
docker-compose down

# 2. Remove old index data
docker volume rm codemcp-opengrok-data

# 3. Start OpenGrok fresh
docker-compose up -d

# 4. Watch logs until indexing completes
docker-compose logs -f opengrok
```

Wait for messages like:
```
Indexing project shortlink
Indexing project codemcp
...
Indexing completed in XX seconds
```

## Alternative: Update docker-compose.yml with absolute path

The `~` in the volume mount might not expand correctly. Try using an absolute path:

```bash
# Edit docker-compose.yml
cd /Users/mustafaacar/codemcp/docker/opengrok
```

Change:
```yaml
- ~/.codemcp/opengrok-workspace:/opengrok/src:ro
```

To:
```yaml
- /Users/mustafaacar/.codemcp/opengrok-workspace:/opengrok/src:ro
```

Then restart:
```bash
docker-compose down
docker volume rm codemcp-opengrok-data
docker-compose up -d
```

## Verify After Fix

1. **Check OpenGrok UI**: http://localhost:8080/source
   - You should see "shortlink" and other projects in the project dropdown

2. **Test API directly**:
   ```bash
   curl http://localhost:8080/source/api/v1/system/ping
   ```

3. **Test search**:
   ```bash
   curl "http://localhost:8080/source/api/v1/search?q=README&project=shortlink"
   ```

## Common Issues

1. **Symlinks not followed**: Make sure Docker Desktop has permission to access the directories
2. **Index corruption**: Always remove the volume when changing workspace paths
3. **Slow indexing**: Large projects can take several minutes to index

Once indexing completes successfully, your MCP agent should be able to use OpenGrok search in the shortlink project.
