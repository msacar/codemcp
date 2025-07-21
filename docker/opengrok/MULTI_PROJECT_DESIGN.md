# OpenGrok Multi-Project Implementation

## Overview

The OpenGrok integration now fully supports multiple projects using OpenGrok's native per-project management capabilities. This aligns perfectly with codemcp's design where each project has its own `codemcp.toml`.

## Key Changes

### 1. Docker Configuration
- Changed from single `PROJECT_PATH` to `OPENGROK_WORKSPACE`
- OpenGrok auto-detects Git repositories as separate projects
- Each project maintains its own search index

### 2. Automatic Project Detection
- Added `get_project_name()` function that detects current project from path
- All search functions now include project filtering
- Searches are automatically scoped to the current project

### 3. Updated Documentation
- Main README now explains multi-project setup
- Docker README includes workspace structure examples
- Updated environment variables and examples

## How It Works

1. **Workspace Structure**:
   ```
   ~/projects/
   ├── project1/
   │   ├── .git/
   │   └── codemcp.toml
   ├── project2/
   │   ├── .git/
   │   └── codemcp.toml
   └── project3/
       ├── .git/
       └── codemcp.toml
   ```

2. **OpenGrok Indexing**:
   - Indexes all Git repositories in workspace
   - Each becomes a separate OpenGrok project
   - Projects are indexed independently

3. **Search Behavior**:
   - When Claude uses search from `project1/`, only `project1` is searched
   - Project detection is automatic based on current path
   - No configuration needed per project

## Benefits

- **No Restart Required**: Switch projects without restarting OpenGrok
- **Isolated Searches**: Each project's searches are independent
- **Scalable**: Add new projects by simply cloning into workspace
- **Backwards Compatible**: Existing search tools still work

## Usage

1. Set up workspace:
   ```bash
   mkdir -p ~/projects
   cd ~/projects
   git clone <project1>
   git clone <project2>
   ```

2. Start OpenGrok:
   ```bash
   ./opengrok.sh start
   ```

3. Work on any project:
   ```bash
   cd ~/projects/project1
   # Claude's searches will automatically be filtered to project1
   ```

## Technical Details

- Uses OpenGrok's `-P` flag for automatic project detection
- Project name is derived from Git repository directory name
- API calls include `project` parameter for filtering
- Falls back gracefully if project detection fails
