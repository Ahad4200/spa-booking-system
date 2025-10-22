#!/usr/bin/env python3
"""
Debug script to test the WebSocket handler with detailed logging
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_websocket_with_logging():
    """Test WebSocket with detailed logging"""
    url = "wss://spa-booking-system.onrender.com/media-stream"
    
    print(f"🔍 Testing WebSocket with detailed logging")
    print(f"🌐 URL: {url}")
    print(f"⏰ Time: {datetime.now()}")
    print("-" * 60)
    
    try:
        print("📡 Connecting to WebSocket...")
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket connection established!")
            print("📊 Connection details:")
            print(f"   - Remote address: {websocket.remote_address}")
            print(f"   - Local address: {websocket.local_address}")
            print(f"   - Protocol: {websocket.subprotocol}")
            print()
            
            # Test 1: Send start event
            print("🧪 Test 1: Sending 'start' event")
            start_message = {
                "event": "start",
                "start": {
                    "streamSid": "debug-stream-123",
                    "callSid": "debug-call-456",
                    "accountSid": "debug-account-789"
                }
            }
            
            print(f"📤 Sending: {json.dumps(start_message, indent=2)}")
            await websocket.send(json.dumps(start_message))
            
            # Wait for any response
            print("⏳ Waiting for response (5 seconds)...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received (timeout)")
            
            # Test 2: Send media event
            print("\n🧪 Test 2: Sending 'media' event")
            media_message = {
                "event": "media",
                "media": {
                    "payload": "dGVzdCBhdWRpbyBkYXRh",  # base64 "test audio data"
                    "timestamp": "1234567890"
                }
            }
            
            print(f"📤 Sending: {json.dumps(media_message, indent=2)}")
            await websocket.send(json.dumps(media_message))
            
            # Wait for any response
            print("⏳ Waiting for response (5 seconds)...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received (timeout)")
            
            # Test 3: Send stop event
            print("\n🧪 Test 3: Sending 'stop' event")
            stop_message = {
                "event": "stop"
            }
            
            print(f"📤 Sending: {json.dumps(stop_message, indent=2)}")
            await websocket.send(json.dumps(stop_message))
            
            # Wait for any response
            print("⏳ Waiting for response (5 seconds)...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received (timeout)")
            
            print("\n✅ WebSocket test completed!")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
        print(f"   Close code: {e.code}")
        print(f"   Close reason: {e.reason}")
    except websockets.exceptions.InvalidURI as e:
        print(f"❌ Invalid WebSocket URI: {e}")
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        import traceback
        traceback.print_exc()

async def test_websocket_ping_pong():
    """Test WebSocket ping/pong to check if connection is alive"""
    url = "wss://spa-booking-system.onrender.com/media-stream"
    
    print(f"\n🏓 Testing WebSocket Ping/Pong")
    print(f"🌐 URL: {url}")
    print("-" * 40)
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket connected for ping test")
            
            # Send ping
            print("📤 Sending ping...")
            await websocket.ping()
            print("✅ Ping sent successfully")
            
            # Wait for pong
            print("⏳ Waiting for pong...")
            try:
                pong_waiter = await websocket.wait_closed()
                print(f"📥 Pong received: {pong_waiter}")
            except Exception as e:
                print(f"📥 Pong response: {e}")
            
    except Exception as e:
        print(f"❌ Ping/Pong test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Detailed WebSocket Debug Test")
    print("=" * 60)
    
    # Test WebSocket with detailed logging
    asyncio.run(test_websocket_with_logging())
    
    # Test ping/pong
    asyncio.run(test_websocket_ping_pong())
    
    print("\n🏁 Detailed debug test completed!")
    print("\n📊 Analysis:")
    print("If no responses were received, the WebSocket handler may have issues with:")
    print("1. Event processing logic")
    print("2. Async/await handling")
    print("3. Message parsing")
    print("4. OpenAI connection setup")
