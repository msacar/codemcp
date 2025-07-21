#!/bin/bash
# Debug script for OpenGrok connectivity

echo "🔍 Debugging OpenGrok Connection Issues"
echo "======================================="

# Check if OpenGrok container is running
echo -e "\n1. Checking Docker container status:"
docker ps | grep codemcp-opengrok || echo "❌ OpenGrok container not running!"

# Check port 8080
echo -e "\n2. Checking port 8080:"
lsof -i :8080 | grep LISTEN || echo "❌ Nothing listening on port 8080!"

# Test OpenGrok API endpoint
echo -e "\n3. Testing OpenGrok API:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/source/api/v1/system/ping || echo "❌ Cannot reach OpenGrok API!"

# Test from Python (same as codemcp does)
echo -e "\n4. Testing from Python:"
python3 -c "
import aiohttp
import asyncio

async def test():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8080/source/api/v1/system/ping', timeout=aiohttp.ClientTimeout(total=5)) as response:
                print(f'✅ OpenGrok API responded with status: {response.status}')
                return response.status == 200
    except Exception as e:
        print(f'❌ Failed to connect: {e}')
        return False

asyncio.run(test())
"

# Check workspace
echo -e "\n5. Checking workspace symlinks:"
ls -la ~/.codemcp/opengrok-workspace/ | grep shortlink || echo "❌ Shortlink project not in workspace!"

# Check docker logs
echo -e "\n6. Recent OpenGrok logs:"
docker logs --tail 10 codemcp-opengrok 2>&1 | grep -E "(error|Error|ERROR|Exception)" || echo "No recent errors in logs"

echo -e "\n7. OpenGrok indexing status:"
docker logs codemcp-opengrok 2>&1 | grep -E "(Indexing|indexed)" | tail -5

# Environment variable check
echo -e "\n8. Checking OPENGROK_URL environment variable:"
echo "OPENGROK_URL=$OPENGROK_URL"
if [ -n "$OPENGROK_URL" ]; then
    echo "⚠️  Custom OPENGROK_URL is set. Testing it:"
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "$OPENGROK_URL/api/v1/system/ping"
fi
