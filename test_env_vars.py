#!/usr/bin/env python3
"""
Test environment variables in the deployed app
"""

import requests
import json

def test_deployed_env():
    print("🔍 Testing environment variables in deployed app...")
    
    # Test the health endpoint first
    try:
        response = requests.get("https://spa-booking-system.onrender.com/", timeout=10)
        print(f"✅ App is running: {response.status_code}")
    except Exception as e:
        print(f"❌ App not accessible: {e}")
        return
    
    # Test if we can trigger a debug endpoint
    try:
        # Try to access a debug endpoint that would show env vars
        response = requests.get("https://spa-booking-system.onrender.com/api/function-handler", timeout=10)
        print(f"📊 Function handler response: {response.status_code}")
        if response.status_code != 200:
            print(f"📝 Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Function handler error: {e}")

if __name__ == "__main__":
    test_deployed_env()
