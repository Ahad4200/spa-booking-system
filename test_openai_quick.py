#!/usr/bin/env python3
"""
Quick test of OpenAI Realtime API connection
"""

import os
import json
import websocket
from dotenv import load_dotenv
import time
import threading

def test_openai_connection():
    # Load environment variables
    load_dotenv(dotenv_path='backend/.env')
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not found")
        return False
    
    print(f"✅ API Key found: {OPENAI_API_KEY[:10]}...")
    
    model = "gpt-4o-mini-realtime-preview-2024-12-17"
    url = f"wss://api.openai.com/v1/realtime?model={model}"
    
    headers = [
        f"Authorization: Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta: realtime=v1"
    ]
    
    print(f"🔌 Testing connection to: {url}")
    
    connected = False
    error_msg = None
    
    def on_open(ws):
        nonlocal connected
        print("✅ Connected to OpenAI!")
        connected = True
        
        # Send session config
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": "You are a test assistant.",
                "voice": "alloy",
                "temperature": 0.7
            }
        }
        ws.send(json.dumps(session_config))
        print("✅ Session configured")
        
        # Close after test
        time.sleep(1)
        ws.close()
    
    def on_message(ws, message):
        data = json.loads(message)
        print(f"📨 Received: {data['type']}")
    
    def on_error(ws, error):
        nonlocal error_msg
        error_msg = str(error)
        print(f"❌ Error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 Connection closed: {close_msg}")
    
    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run in thread
    wst = threading.Thread(target=ws.run_forever, daemon=True)
    wst.start()
    
    # Wait for result
    timeout = 10
    start_time = time.time()
    while not connected and not error_msg and (time.time() - start_time) < timeout:
        time.time()
    
    wst.join(timeout=5)
    
    if connected:
        print("🎉 OpenAI connection successful!")
        return True
    else:
        print(f"❌ OpenAI connection failed: {error_msg}")
        return False

if __name__ == "__main__":
    test_openai_connection()
