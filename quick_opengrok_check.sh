#!/bin/bash
# Quick OpenGrok diagnostics

echo "🐳 Docker & OpenGrok Status Check"
echo "================================="

# 1. Check if Docker is running
echo -e "\n1. Docker daemon status:"
docker version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Docker is running"
else
    echo "   ❌ Docker is not running!"
    echo "   Start Docker Desktop and try again"
    exit 1
fi

# 2. Check OpenGrok container
echo -e "\n2. OpenGrok container status:"
CONTAINER_STATUS=$(docker ps --filter "name=codemcp-opengrok" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}")
if [ -z "$CONTAINER_STATUS" ]; then
    echo "   ❌ OpenGrok container is not running!"
    echo "   Run: cd docker/opengrok && docker-compose up -d"
else
    echo "$CONTAINER_STATUS"
fi

# 3. Check port 8080
echo -e "\n3. Port 8080 status:"
if command -v lsof > /dev/null; then
    lsof -i :8080 | grep LISTEN || echo "   ❌ Nothing listening on port 8080"
else
    netstat -an | grep 8080 | grep LISTEN || echo "   ❌ Nothing listening on port 8080"
fi

# 4. Test localhost:8080
echo -e "\n4. Testing http://localhost:8080/source/api/v1/system/ping:"
curl -s -w "\n   HTTP Status: %{http_code}\n   Response: " http://localhost:8080/source/api/v1/system/ping && echo

# 5. Check if it's a different port or host
echo -e "\n5. Alternative endpoints to try:"
echo "   - http://127.0.0.1:8080/source/api/v1/system/ping"
echo "   - http://0.0.0.0:8080/source/api/v1/system/ping"

# Test 127.0.0.1
curl -s -o /dev/null -w "   127.0.0.1:8080 - HTTP Status: %{http_code}\n" http://127.0.0.1:8080/source/api/v1/system/ping

# 6. Docker logs
echo -e "\n6. Last 5 lines of OpenGrok logs:"
docker logs --tail 5 codemcp-opengrok 2>&1 || echo "   Cannot get logs"

# 7. Check workspace
echo -e "\n7. Workspace check:"
if [ -d ~/.codemcp/opengrok-workspace ]; then
    echo "   Projects in workspace:"
    ls -la ~/.codemcp/opengrok-workspace/ | grep -E "^l" | awk '{print "   - " $9 " -> " $11}'
else
    echo "   ❌ Workspace directory not found!"
fi
