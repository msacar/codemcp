# Project Registration Quick Fix

If you're getting import errors when running `codemcp` after this update, you need to reinstall to get the new dependencies:

## For local development:
```bash
cd /Users/mustafaacar/codemcp
uv pip install -e ".[dev]"
```

## For uvx users:
The new dependencies (tabulate, aiofiles) need to be installed. Try:

```bash
# Option 1: Force reinstall
uvx --reinstall --from git+https://github.com/ezyang/codemcp@main codemcp serve

# Option 2: Use local installation
cd /path/to/codemcp
uv pip install -e .
python -m codemcp serve
```

## Verify installation:
```bash
# Check if project commands work
python -m codemcp project --help
```

## Dependencies added:
- `tabulate>=0.9.0` - For formatting project lists
- `aiofiles>=0.12.0` - For async file operations in project registry
