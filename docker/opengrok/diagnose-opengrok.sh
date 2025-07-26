#!/bin/bash

echo "=== OpenGrok Diagnostic and Restart Script ==="

# Stop OpenGrok
echo "Stopping OpenGrok container..."
docker-compose down

# Clean up old data if requested
if [ "$1" == "--clean" ]; then
    echo "Cleaning OpenGrok data volume..."
    docker volume rm codemcp-opengrok-data || true
fi

# Start OpenGrok with increased logging
echo "Starting OpenGrok with verbose logging..."
docker-compose up -d

# Wait for container to start
echo "Waiting for container to start..."
sleep 5

# Follow logs with timestamps
echo "Following logs (Ctrl+C to stop)..."
docker logs -f --timestamps codemcp-opengrok
