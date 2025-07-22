#!/usr/bin/env python3
"""Quick test to check OpenGrok connection."""

import asyncio
import aiohttp


async def test_connection():
    print("Testing OpenGrok connection...")
    print("URL: http://localhost:8080")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8080/source/api/v1/system/ping",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                print(f"Status: {response.status}")
                text = await response.text()
                print(f"Response: {text}")

                if response.status == 200:
                    print("✅ OpenGrok is running!")
                else:
                    print("❌ OpenGrok returned non-200 status")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPossible issues:")
        print("1. OpenGrok is not running")
        print("2. It's running on a different port")
        print("3. Firewall/network issues")

    # Also try 127.0.0.1
    print("\nTrying 127.0.0.1...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://127.0.0.1:8080/source/api/v1/system/ping",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    print("✅ Works with 127.0.0.1!")
    except Exception as e:
        print(f"❌ Also failed with 127.0.0.1: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())
