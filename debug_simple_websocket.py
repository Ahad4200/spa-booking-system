#!/usr/bin/env python3
"""
Simple WebSocket test to identify the exact issue
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_simple_websocket():
    """Test with a very simple WebSocket connection"""
    url = "wss://spa-booking-system.onrender.com/media-stream"
    
    print(f"🔍 Simple WebSocket Test")
    print(f"🌐 URL: {url}")
    print(f"⏰ Time: {datetime.now()}")
    print("-" * 50)
    
    try:
        print("📡 Connecting...")
        async with websockets.connect(url) as websocket:
            print("✅ Connected!")
            
            # Send a simple message
            simple_message = {"test": "hello"}
            print(f"📤 Sending: {simple_message}")
            await websocket.send(json.dumps(simple_message))
            
            # Wait for response
            print("⏳ Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                print(f"📥 Response: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response (timeout)")
            
            # Check if connection is still alive
            print("🔍 Checking connection status...")
            if websocket.closed:
                print("❌ Connection closed")
            else:
                print("✅ Connection still alive")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_websocket())
