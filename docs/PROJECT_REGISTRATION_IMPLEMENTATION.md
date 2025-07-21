# Project Registration Implementation Summary

## Overview

Implemented a manual project registration system for codemcp that allows users to explicitly map project names to filesystem paths, enabling work with projects located anywhere on the system.

## Key Components

### 1. Core Module: `codemcp/project_registry.py`
- `ProjectRegistry` class manages project mappings
- Stores configuration in `~/.codemcp/projects.toml`
- Creates symlinks in `~/.codemcp/opengrok-workspace/`
- Provides project detection for any filesystem path

### 2. CLI Interface: `codemcp/cli/project.py`
- `project register` - Register new projects
- `project unregister` - Remove projects
- `project list` - Show all projects with status
- `project sync` - Recreate workspace symlinks
- `project which` - Find project for a given path

### 3. Integration Points

#### OpenGrok Integration
- Modified `get_project_name()` in `opengrok_search.py` to check registry first
- Falls back to Git-based detection if not found in registry
- Seamless project switching without OpenGrok restart

#### Docker Configuration
- Users update docker-compose.yml to mount `~/.codemcp/opengrok-workspace`
- OpenGrok sees symlinks as regular directories
- All registered projects get indexed automatically

## Architecture Decisions

### Why Symlinks?
- Maintains OpenGrok's single mount point requirement
- Projects appear as subdirectories to OpenGrok
- Simple, reliable, cross-platform solution
- No need for complex Docker volume management

### Why Manual Registration?
- Explicit control over what gets indexed
- No surprises from automatic discovery
- Clear project naming independent of filesystem paths
- Easy to understand and debug

## User Workflow

1. **Register a project**:
   ```bash
   codemcp project register myapp /any/path/to/myapp
   ```

2. **Work normally**:
   ```bash
   cd /any/path/to/myapp
   # Claude operations automatically scoped to 'myapp'
   ```

3. **Manage projects**:
   ```bash
   codemcp project list
   codemcp project sync
   ```

## Benefits

- **Flexibility**: Projects can be anywhere - different drives, network mounts, user directories
- **Backward Compatible**: Existing Git detection still works
- **Simple**: No complex configuration or Git integration needed
- **Transparent**: Easy to see what's registered and troubleshoot issues
- **Fast**: No repository scanning or network operations

## Testing

- Unit tests: `tests/test_project_registry.py`
- E2E tests: `e2e/test_project_cli.py`
- Example script: `examples/project_registration_demo.py`

## Documentation

- User guide: `docs/PROJECT_REGISTRATION.md`
- Migration guide: `docs/MIGRATION_PROJECT_REGISTRATION.md`
- Updated README with project registration section

## Future Enhancements

Potential improvements that could be added:

1. **Project Templates**: Define common commands per project type
2. **Project Groups**: Organize related projects together
3. **Auto-discovery Mode**: Optional scanning for projects with codemcp.toml
4. **Project Switching**: CLI command to quickly cd to a registered project
5. **Import/Export**: Share project registrations between machines

## Implementation Notes

- Uses TOML for configuration (consistent with codemcp.toml)
- Async/await throughout for consistency with MCP architecture
- Proper error handling and user feedback
- Follows existing codemcp patterns and conventions
