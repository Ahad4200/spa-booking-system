#!/usr/bin/env python3
"""
Test script for the debug WebSocket handler
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_debug_handler():
    """Test the debug WebSocket handler"""
    url = "wss://spa-booking-system.onrender.com/media-stream"
    
    print(f"🔍 Testing Debug WebSocket Handler")
    print(f"🌐 URL: {url}")
    print(f"⏰ Time: {datetime.now()}")
    print("-" * 60)
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket connected!")
            
            # Test 1: Send start event
            print("\n🧪 Test 1: Sending 'start' event")
            start_message = {
                "event": "start",
                "start": {
                    "streamSid": "test-stream-123",
                    "callSid": "test-call-456"
                }
            }
            
            print(f"📤 Sending: {json.dumps(start_message, indent=2)}")
            await websocket.send(json.dumps(start_message))
            
            # Wait for response
            print("⏳ Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Response: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received")
            
            # Test 2: Send media event
            print("\n🧪 Test 2: Sending 'media' event")
            media_message = {
                "event": "media",
                "media": {
                    "payload": "dGVzdCBhdWRpbyBkYXRh"
                }
            }
            
            print(f"📤 Sending: {json.dumps(media_message, indent=2)}")
            await websocket.send(json.dumps(media_message))
            
            # Wait for response
            print("⏳ Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Response: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received")
            
            # Test 3: Send stop event
            print("\n🧪 Test 3: Sending 'stop' event")
            stop_message = {"event": "stop"}
            
            print(f"📤 Sending: {json.dumps(stop_message, indent=2)}")
            await websocket.send(json.dumps(stop_message))
            
            print("\n✅ Debug test completed!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_debug_handler())
