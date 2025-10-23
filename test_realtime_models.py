#!/usr/bin/env python3
"""
Test different OpenAI Realtime API model names
"""

import os
import json
import websocket
from dotenv import load_dotenv
import time
import threading

def test_model(model_name):
    load_dotenv(dotenv_path='backend/.env')
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    
    url = f"wss://api.openai.com/v1/realtime?model={model_name}"
    headers = [
        f"Authorization: Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta: realtime=v1"
    ]
    
    print(f"🔌 Testing model: {model_name}")
    print(f"   URL: {url}")
    
    connected = False
    error_msg = None
    
    def on_open(ws):
        nonlocal connected
        print(f"   ✅ Connected to {model_name}!")
        connected = True
        ws.close()
    
    def on_error(ws, error):
        nonlocal error_msg
        error_msg = str(error)
        print(f"   ❌ Error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"   🔌 Closed: {close_msg}")
    
    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_error=on_error,
        on_close=on_close
    )
    
    wst = threading.Thread(target=ws.run_forever, daemon=True)
    wst.start()
    
    timeout = 5
    start_time = time.time()
    while not connected and not error_msg and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    wst.join(timeout=2)
    
    if connected:
        print(f"   🎉 {model_name} works!")
        return True
    else:
        print(f"   ❌ {model_name} failed: {error_msg}")
        return False

def main():
    models_to_test = [
        "gpt-4o-mini-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview",
        "gpt-4o-mini-realtime",
        "gpt-4o-realtime",
        "gpt-4o-mini"
    ]
    
    print("🤖 Testing OpenAI Realtime API Models")
    print("=" * 50)
    
    working_models = []
    for model in models_to_test:
        if test_model(model):
            working_models.append(model)
        print()
    
    print("=" * 50)
    if working_models:
        print(f"✅ Working models: {', '.join(working_models)}")
    else:
        print("❌ No models are working")

if __name__ == "__main__":
    main()
