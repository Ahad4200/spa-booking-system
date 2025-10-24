# test_websocket_endpoint.py
import asyncio
import websockets
import json

async def test_websocket_connection():
    """Test if the WebSocket endpoint is accessible"""
    url = "wss://spa-booking-system.onrender.com/media-stream"
    
    try:
        print(f"🔌 Testing WebSocket connection to: {url}")
        
        async with websockets.connect(url) as ws:
            print("✅ WebSocket connection successful!")
            
            # Send a test message
            test_message = {
                "event": "start",
                "start": {
                    "streamSid": "test-stream-123",
                    "callSid": "test-call-123"
                }
            }
            
            await ws.send(json.dumps(test_message))
            print("✅ Test message sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"✅ Received response: {response}")
            except asyncio.TimeoutError:
                print("⚠️  No response received (timeout)")
            
            return True
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed with status {e.status_code}")
        if e.status_code == 404:
            print("   → The /media-stream endpoint is not found (404)")
            print("   → This means the FastAPI WebSocket handler is not registered")
        elif e.status_code == 500:
            print("   → Server error (500) - check application logs")
        return False
        
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing WebSocket Endpoint")
    print("="*50)
    
    result = asyncio.run(test_websocket_connection())
    
    if result:
        print("\n✅ WebSocket endpoint is working!")
    else:
        print("\n❌ WebSocket endpoint has issues!")
        print("\n🔧 Possible fixes:")
        print("   1. Check if FastAPI WebSocket handler is properly registered")
        print("   2. Verify the app.py file has no syntax errors")
        print("   3. Check if the deployment includes the WebSocket handler")
