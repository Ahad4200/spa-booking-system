# test_openai_websocket.py
import asyncio
import websockets
import json
import os
import sys

async def test_openai_connection():
    """Test OpenAI Realtime API connection and text conversation"""
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
    
    try:
        print("\n" + "="*60)
        print("🔌 CONNECTING TO OPENAI REALTIME API")
        print("="*60)
        
        async with websockets.connect(
            url,
            extra_headers={
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as ws:
            print("✅ Connected to OpenAI Realtime API\n")
            
            # Configure session
            print("📋 Configuring session...")
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "instructions": "You are Sara, a friendly spa receptionist. Keep responses concise and natural. Help with massage bookings.",
                    "voice": "alloy",
                    "temperature": 0.7
                }
            }
            await ws.send(json.dumps(session_config))
            
            # Wait for session confirmation
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            if data.get('type') == 'session.updated':
                print("✅ Session configured successfully\n")
            else:
                print(f"⚠️  Unexpected response type: {data.get('type')}\n")
            
            # Send test message
            print("💬 Sending test message...")
            test_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": "Ciao, vorrei prenotare un massaggio per domani alle 15:00. Quanto costa?"
                    }]
                }
            }
            await ws.send(json.dumps(test_message))
            print("✅ Message sent\n")
            
            # Request AI response
            print("⏳ Waiting for AI response...\n")
            print("="*60)
            print("🤖 AI RESPONSE:")
            print("="*60)
            
            await ws.send(json.dumps({"type": "response.create"}))
            
            response_text = ""
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(response)
                    
                    if data['type'] == 'response.text.delta':
                        text_chunk = data.get('delta', '')
                        print(text_chunk, end='', flush=True)
                        response_text += text_chunk
                        
                    elif data['type'] == 'response.text.done':
                        full_text = data.get('text', '')
                        print(f"\n\n{'='*60}")
                        print("✅ COMPLETE RESPONSE RECEIVED")
                        print(f"{'='*60}\n")
                        
                        print("✅ SUCCESS: OpenAI Realtime API is working!")
                        print(f"   Response: {full_text[:100]}...\n")
                        return True
                        
                    elif data['type'] == 'response.done':
                        break
                        
                except asyncio.TimeoutError:
                    print("\n\n❌ TIMEOUT: No response from OpenAI after 10 seconds")
                    return False
                    
            return bool(response_text)
            
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket connection failed: {e}")
        print("   Check: API key validity, network connectivity, firewall rules")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

# Run test
print("\n🧪 TESTING OPENAI REALTIME API")
print("(This is a text-only test, not audio)\n")

result = asyncio.run(test_openai_connection())

if result:
    print("🎉 OpenAI integration is ready for production!")
else:
    print("❌ OpenAI integration has issues. Check logs above.")
    sys.exit(1)
