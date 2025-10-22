#!/usr/bin/env python3
"""
Debug script to test WebSocket connection to spa-booking-system
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_websocket_connection():
    """Test WebSocket connection to the spa booking system"""
    url = "wss://spa-booking-system.onrender.com/media-stream"
    
    print(f"🔍 Testing WebSocket connection to: {url}")
    print(f"⏰ Time: {datetime.now()}")
    print("-" * 50)
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket connection established!")
            
            # Send a test message (simulating Twilio start event)
            test_message = {
                "event": "start",
                "start": {
                    "streamSid": "test-stream-123",
                    "callSid": "test-call-456",
                    "accountSid": "test-account-789"
                }
            }
            
            print(f"📤 Sending test message: {json.dumps(test_message, indent=2)}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            print("⏳ Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"📥 Received response: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received within 10 seconds")
            
            # Send media event
            media_message = {
                "event": "media",
                "media": {
                    "payload": "dGVzdCBhdWRpbyBkYXRh"  # base64 encoded "test audio data"
                }
            }
            
            print(f"📤 Sending media message: {json.dumps(media_message, indent=2)}")
            await websocket.send(json.dumps(media_message))
            
            # Wait for response
            print("⏳ Waiting for media response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"📥 Received media response: {response}")
            except asyncio.TimeoutError:
                print("⏰ No media response received within 10 seconds")
            
            # Send stop event
            stop_message = {
                "event": "stop"
            }
            
            print(f"📤 Sending stop message: {json.dumps(stop_message, indent=2)}")
            await websocket.send(json.dumps(stop_message))
            
            print("✅ WebSocket test completed successfully!")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except websockets.exceptions.InvalidURI as e:
        print(f"❌ Invalid WebSocket URI: {e}")
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        import traceback
        traceback.print_exc()

async def test_http_endpoints():
    """Test HTTP endpoints"""
    import aiohttp
    
    print("\n" + "=" * 50)
    print("🔍 Testing HTTP endpoints")
    print("=" * 50)
    
    endpoints = [
        "https://spa-booking-system.onrender.com/",
        "https://spa-booking-system.onrender.com/webhook/incoming-call",
        "https://spa-booking-system.onrender.com/webhook/call-status"
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                print(f"📡 Testing: {endpoint}")
                async with session.get(endpoint) as response:
                    print(f"   Status: {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}...")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            print()

if __name__ == "__main__":
    print("🚀 Starting WebSocket Debug Test")
    print("=" * 50)
    
    # Test HTTP endpoints first
    asyncio.run(test_http_endpoints())
    
    # Test WebSocket connection
    asyncio.run(test_websocket_connection())
    
    print("\n🏁 Debug test completed!")
