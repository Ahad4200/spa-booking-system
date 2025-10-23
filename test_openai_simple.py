#!/usr/bin/env python3
"""
Test OpenAI API with simple HTTP request first
"""

import os
import requests
from dotenv import load_dotenv

def test_openai_api():
    # Load environment variables
    load_dotenv(dotenv_path='backend/.env')
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not found")
        return False
    
    print(f"✅ API Key found: {OPENAI_API_KEY[:10]}...")
    
    # Test with simple chat completion first
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }
    
    print("🔌 Testing OpenAI API with simple request...")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OpenAI API is working!")
            print(f"📝 Response: {result['choices'][0]['message']['content']}")
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"📝 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    test_openai_api()
