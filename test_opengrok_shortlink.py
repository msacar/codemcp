#!/usr/bin/env python3
"""Test OpenGrok connection and project detection for shortlink project."""

import asyncio
import os
import sys

sys.path.insert(0, "/Users/mustafaacar/codemcp")

from codemcp.tools.opengrok_search import (
    check_opengrok_status,
    get_project_name,
    get_opengrok_url,
    opengrok_file_search,
)


async def test_opengrok_connection():
    print("🔍 Testing OpenGrok Connection for Shortlink Project\n")

    # 1. Check OpenGrok URL
    url = await get_opengrok_url()
    print(f"1. OpenGrok URL: {url}")
    print(f"   OPENGROK_URL env: {os.environ.get('OPENGROK_URL', 'Not set')}")

    # 2. Test OpenGrok status
    print("\n2. Testing OpenGrok status...")
    status = await check_opengrok_status()
    print(f"   OpenGrok available: {'✅ Yes' if status else '❌ No'}")

    # 3. Test project detection
    print("\n3. Testing project detection...")
    project_path = "/Users/mustafaacar/retter/shortlink"
    project_name = await get_project_name(project_path)
    print(f"   Path: {project_path}")
    print(f"   Detected project: {project_name or 'None'}")

    # 4. Try a file search
    if status:
        print("\n4. Testing file search...")
        try:
            result = await opengrok_file_search(
                filename="README.md", path=project_path, chat_id="test"
            )
            print(f"   Search result preview: {result[:200]}...")
        except Exception as e:
            print(f"   ❌ Search failed: {e}")

    # 5. Direct API test
    print("\n5. Direct API test...")
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            test_url = f"{url}/api/v1/system/ping"
            async with session.get(
                test_url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                print(f"   API ping status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   API response: {data}")
    except Exception as e:
        print(f"   ❌ Direct API test failed: {e}")

    # 6. Check symlink
    print("\n6. Checking workspace symlink...")
    symlink_path = os.path.expanduser("~/.codemcp/opengrok-workspace/shortlink")
    if os.path.islink(symlink_path):
        target = os.readlink(symlink_path)
        print(f"   ✅ Symlink exists: {symlink_path} -> {target}")
    else:
        print(f"   ❌ Symlink not found: {symlink_path}")


if __name__ == "__main__":
    asyncio.run(test_opengrok_connection())
