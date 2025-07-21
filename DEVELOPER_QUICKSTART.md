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

