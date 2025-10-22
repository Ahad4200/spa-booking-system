#!/usr/bin/env python3
"""
Debug script to monitor Render logs and service status
"""

import requests
import json
import time
from datetime import datetime

def test_service_health():
    """Test service health endpoints"""
    print("🔍 Testing Service Health")
    print("=" * 40)
    
    endpoints = [
        "https://spa-booking-system.onrender.com/",
        "https://spa-booking-system.onrender.com/health",
        "https://spa-booking-system.onrender.com/webhook/incoming-call"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"📡 Testing: {endpoint}")
            response = requests.get(endpoint, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            print(f"   Headers: {dict(response.headers)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()

def test_websocket_endpoint():
    """Test WebSocket endpoint accessibility"""
    print("🔍 Testing WebSocket Endpoint")
    print("=" * 40)
    
    # Test if the WebSocket endpoint is accessible
    try:
        # Try to connect to WebSocket endpoint
        import websockets
        import asyncio
        
        async def test_ws():
            try:
                async with websockets.connect("wss://spa-booking-system.onrender.com/media-stream") as ws:
                    print("✅ WebSocket connection successful!")
                    return True
            except Exception as e:
                print(f"❌ WebSocket connection failed: {e}")
                return False
        
        result = asyncio.run(test_ws())
        return result
        
    except ImportError:
        print("❌ websockets library not available")
        return False
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")
        return False

def test_webhook_simulation():
    """Simulate a webhook call"""
    print("🔍 Testing Webhook Simulation")
    print("=" * 40)
    
    # Simulate Twilio webhook call
    webhook_data = {
        "CallSid": "test-call-123",
        "From": "+1234567890",
        "To": "+13412175012",
        "CallStatus": "ringing",
        "Direction": "inbound"
    }
    
    try:
        print("📤 Sending webhook simulation...")
        response = requests.post(
            "https://spa-booking-system.onrender.com/webhook/incoming-call",
            data=webhook_data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Webhook simulation successful!")
            return True
        else:
            print("❌ Webhook simulation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Webhook simulation error: {e}")
        return False

def monitor_call_events(call_sid):
    """Monitor specific call events"""
    print(f"🔍 Monitoring Call Events for: {call_sid}")
    print("=" * 50)
    
    # This would require Twilio API access
    print("📞 Call SID:", call_sid)
    print("⏰ Time:", datetime.now())
    print("📊 Status: Monitoring...")
    
    # In a real implementation, you would poll Twilio API
    # For now, just show the call SID for reference
    return call_sid

def main():
    """Main debug function"""
    print("🚀 Starting Render Debug Monitor")
    print("=" * 50)
    print(f"⏰ Time: {datetime.now()}")
    print()
    
    # Test service health
    test_service_health()
    
    # Test WebSocket endpoint
    ws_success = test_websocket_endpoint()
    
    # Test webhook simulation
    webhook_success = test_webhook_simulation()
    
    # Summary
    print("📊 Debug Summary")
    print("=" * 30)
    print(f"WebSocket Connection: {'✅ Success' if ws_success else '❌ Failed'}")
    print(f"Webhook Simulation: {'✅ Success' if webhook_success else '❌ Failed'}")
    
    if not ws_success:
        print("\n🔧 Troubleshooting Tips:")
        print("1. Check if Render deployment is complete")
        print("2. Verify WebSocket endpoint is accessible")
        print("3. Check Render logs for errors")
        print("4. Ensure flask-sock is properly installed")
    
    if not webhook_success:
        print("\n🔧 Webhook Troubleshooting:")
        print("1. Check if Flask app is running")
        print("2. Verify webhook routes are working")
        print("3. Check for Python errors in logs")

if __name__ == "__main__":
    main()
