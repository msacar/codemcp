#!/bin/bash
# Restart OpenGrok with fresh index after changing projects

set -e

echo "🔄 Restarting OpenGrok with fresh index..."
echo "========================================="

# Change to docker directory
cd "$(dirname "$0")/../docker/opengrok"

echo -e "\n1. Stopping OpenGrok..."
docker-compose down

echo -e "\n2. Removing old index data..."
docker volume rm codemcp-opengrok-data 2>/dev/null || echo "   (No existing index to remove)"

echo -e "\n3. Starting OpenGrok..."
docker-compose up -d

echo -e "\n4. Waiting for OpenGrok to start..."
sleep 5

echo -e "\n5. Monitoring indexing progress..."
echo "   (Press Ctrl+C to stop monitoring)"
echo ""
docker logs -f codemcp-opengrok 2>&1 | grep -E "(Indexing|indexed|done|completed|Project|Source:|finished)"
