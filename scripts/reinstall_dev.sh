#!/bin/bash
# Reinstall codemcp in development mode to pick up code changes

set -e

echo "🔄 Reinstalling codemcp in development mode..."
echo "============================================"

# Change to project root
cd "$(dirname "$0")/.."

echo -e "\n1. Uninstalling any existing installation..."
uv pip uninstall codemcp -y 2>/dev/null || echo "   (No existing installation)"

echo -e "\n2. Installing in development mode..."
uv pip install -e .

echo -e "\n3. Verifying installation..."
which codemcp

echo -e "\n✅ Done! The codemcp command now uses your local development code."
echo "   Any changes you make will be reflected immediately."
