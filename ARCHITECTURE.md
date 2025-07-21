# codemcp Architecture

This document provides an overview of the architecture and design decisions of codemcp.

## Project Configuration

The codemcp tool uses a TOML file (`codemcp.toml`) in the project root for configuration. This file has several sections:

### Project Prompt

The `project_prompt` string is included in system prompts to provide project-specific instructions to Claude.

```toml
project_prompt = """
Project-specific instructions for Claude go here.
"""
```

### Commands

The `commands` section specifies commands that can be executed by specialized tools at specific times. Commands are defined as arrays of strings that will be joined with spaces and executed in a shell context:

```toml
[commands]
format = ["./run_format.sh"]
```

Currently supported commands:
- `format`: Used by the Format tool to format code according to project standards.

### OpenGrok Configuration (Optional)

OpenGrok integration can be configured for advanced code search capabilities:

```toml
[opengrok]
enabled = false  # Set to true to enable OpenGrok features
url = "http://localhost:8080/source"  # OpenGrok server URL
```

You can also set the OpenGrok URL via environment variable:
```bash
export OPENGROK_URL=http://your-server:8080/source
```

## Tools

codemcp provides several tools that Claude can use during interaction:

### Core File Operations
- **ReadFile**: Read a file from the filesystem
- **WriteFile**: Write content to a file
- **EditFile**: Make targeted edits to a file
- **LS**: List files and directories
- **Grep**: Search for patterns in files using git grep
- **Glob**: Find files matching patterns
- **SmartSearch**: JavaScript/TypeScript-specific search tools

### Project Management
- **InitProject**: Initialize a project and load its configuration
- **ProjectOverview**: Get a high-level view of project structure
- **Format**: Format code according to project standards using the configured command
- **RunCommand**: Execute pre-configured commands from codemcp.toml

### Git Operations
- **GitLog**: View commit history
- **GitDiff**: Show differences between commits
- **GitShow**: Show commit details
- **GitBlame**: Show who changed what and when

### Advanced Search (OpenGrok Integration)
When OpenGrok is running (optional Docker service), these additional tools become available:
- **opengrok_search**: Full-text semantic search with language awareness
- **opengrok_file_search**: Efficient file name/pattern search
- **opengrok_definition_search**: Find symbol definitions (classes, functions, variables)
- **opengrok_reference_search**: Find all references to a symbol
- **check_opengrok_status**: Check if OpenGrok service is available

OpenGrok provides superior search capabilities for large codebases with:
- Pre-indexed searches for speed
- Language-aware parsing
- Cross-reference navigation
- Search in git history

## System Integration

When a project is initialized using `InitProject`, codemcp reads the `codemcp.toml` file and constructs a system prompt that includes:

1. Default system instructions
2. The project's `project_prompt`
3. Instructions to use specific tools at appropriate times

For example, if a format command is configured, the system prompt will include an instruction for Claude to use the Format tool when the task is complete.
