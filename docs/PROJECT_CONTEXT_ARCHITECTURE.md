# Project Context in MCP Server Architecture

## The Challenge

When multiple projects (project-a, project-b, etc.) use the same MCP server instance, we need to determine which project is making each request. This is crucial for:

1. OpenGrok searches - to filter results to the correct project
2. File operations - to ensure paths are resolved correctly
3. Command execution - to run in the right project context

## How It Works

### 1. Project Initialization

When a user starts working with a project, they call `init_project` with a directory path:

```
Initialize codemcp for /Users/me/work/project-a
```

This establishes the **project context** for that conversation/session.

### 2. Path Resolution

All file-related tools in codemcp expect **absolute paths** or paths that can be resolved relative to the initialized project:

- `read_file("/Users/me/work/project-a/src/main.py")`
- `edit_file(path="/Users/me/work/project-a/README.md", ...)`
- `opengrok_search(query="TODO", path="/Users/me/work/project-a/src")`

### 3. Project Detection Flow

When OpenGrok search tools are called:

```python
# In opengrok_search.py
async def get_project_name(path: Optional[str] = None) -> Optional[str]:
    if not path:
        return None

    # 1. First check project registry
    registry = await get_registry()
    project_name = await registry.get_project_for_path(path)
    if project_name:
        return project_name

    # 2. Fall back to Git detection
    git_root = await find_git_root(path)
    if git_root:
        return os.path.basename(git_root)

    return None
```

### 4. Example Workflow

1. **Project A starts a session:**
   ```
   init_project(directory="/Users/me/work/project-a")
   ```

2. **Project A searches for something:**
   ```
   opengrok_search(query="authentication", path="/Users/me/work/project-a")
   ```
   - Path provided → detects "project-a" from registry
   - OpenGrok filters search to project-a only

3. **Project B starts a different session:**
   ```
   init_project(directory="/mnt/server/project-b")
   ```

4. **Project B searches:**
   ```
   opengrok_search(query="authentication", path="/mnt/server/project-b/src")
   ```
   - Path provided → detects "project-b" from registry
   - OpenGrok filters search to project-b only

## Best Practices

### Always Provide Paths

When using OpenGrok search tools, always provide the path parameter:

```python
# Good - project can be determined
opengrok_search(query="TODO", path="/current/working/directory")

# Bad - no way to determine project
opengrok_search(query="TODO")  # Which project???
```

### Register Projects Before Use

Before using OpenGrok with a project:

```bash
# Register the project
codemcp project register myproject /path/to/myproject

# Then work with it
cd /path/to/myproject
# Initialize and use MCP tools
```

### Project Isolation

Each project's searches are automatically isolated:
- Project A searching for "User" won't see results from Project B
- This happens automatically based on the path context

## Technical Details

### MCP Server State

The MCP server itself is **stateless** between tool calls. It doesn't maintain a "current project" in memory. Instead:

1. Each tool call must include enough context (usually a path)
2. The project is determined fresh for each call
3. This ensures correct behavior even with concurrent requests

### Concurrent Usage

Multiple projects can use the same MCP server simultaneously because:
- No shared state between requests
- Project detection based on provided paths
- OpenGrok supports multi-project indexing natively

### Docker Volume Mapping

The docker-compose.yml uses direct bind mounts for each project:
```yaml
volumes:
  - /Users/me/work/project-a:/opengrok/src/project-a:ro
  - /mnt/server/project-b:/opengrok/src/project-b:ro
  - /home/shared/project-c:/opengrok/src/project-c:ro
  # Each project mounted separately
```

OpenGrok sees these as regular directories and indexes them as separate projects.

## Limitations

1. **Path Required**: OpenGrok tools need a path parameter to determine the project
2. **No Implicit Context**: The server doesn't "remember" which project you're working on
3. **Registration Needed**: Projects must be registered before OpenGrok can index them

## Future Improvements

Potential enhancements could include:

1. **Session Context**: Maintain project context within a conversation session
2. **Default Project**: Configure a default project for path-less searches
3. **Smart Detection**: Infer project from other tool calls in the same session
