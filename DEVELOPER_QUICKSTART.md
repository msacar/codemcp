# Remove old venv
rm -rf .venv

# Create new one with uv
uv venv --python 3.12

# Activate it (for fish shell)
source .venv/bin/activate.fish

# Install dependencies
uv pip install -e ".[dev]"
# Fallback to Install dependencies
uv pip install --group dev

# Start Using absolute path with uvx
uvx --from /Users/mustafaacar/codemcp codemcp serve
uvx --python 3.12 --from /Users/mustafaacar/codemcp codemcp serve

# Tree-sitter issue keep in mind 
Fixed the tree-sitter initialization issue - The tree-sitter-languages package was failing to initialize with "init() takes exactly 1 argument (2 given)". This appears to be a version compatibility issue.

