#!/bin/bash
# Script to properly restart OpenGrok with new workspace

echo "🔧 Fixing OpenGrok indexing for project registration workspace"
echo "============================================================="

cd /Users/mustafaacar/codemcp/docker/opengrok

echo -e "\n1. Stopping OpenGrok..."
docker-compose down

echo -e "\n2. Cleaning old index data..."
docker volume rm codemcp-opengrok-data || echo "No old data to remove"

echo -e "\n3. Checking workspace symlinks..."
echo "Projects in workspace:"
ls -la ~/.codemcp/opengrok-workspace/

echo -e "\n4. Starting OpenGrok with fresh index..."
docker-compose up -d

echo -e "\n5. Waiting for container to be ready..."
sleep 10

echo -e "\n6. Monitoring indexing progress..."
echo "Watching logs (press Ctrl+C when you see 'Indexing completed'):"
docker-compose logs -f opengrok | grep -E "(Indexing|indexed|Project|Error|WARNING)"
