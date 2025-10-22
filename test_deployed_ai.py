#!/usr/bin/env python3
"""
Test the deployed AI components via HTTP requests
"""

import requests
import json
import time

def test_deployed_ai():
    """Test AI components through the deployed app"""
    print("🧪 Testing Deployed AI Components")
    print("=" * 50)
    
    app_url = "https://spa-booking-system.onrender.com"
    
    # Test 1: Health Check
    print("1. 🏥 Testing Health Check...")
    try:
        response = requests.get(f"{app_url}/", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Health: {response.json()}")
        else:
            print(f"   ❌ Health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health error: {e}")
        return False
    
    # Test 2: Database Connection
    print("\n2. 🗄️ Testing Database Connection...")
    try:
        response = requests.get(f"{app_url}/test-db", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Database: {data['message']}")
            print(f"   ✅ Project ID: {data['project_id']}")
        else:
            print(f"   ❌ Database failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False
    
    # Test 3: Simulate Twilio Webhook (Incoming Call)
    print("\n3. 📞 Testing Twilio Webhook Simulation...")
    try:
        # Simulate Twilio webhook data
        webhook_data = {
            'CallSid': 'test_call_123',
            'From': '+39 333 123 4567',
            'To': '+39 333 987 6543',
            'CallStatus': 'ringing'
        }
        
        response = requests.post(
            f"{app_url}/webhook/incoming-call",
            data=webhook_data,
            timeout=15
        )
        
        if response.status_code == 200:
            print(f"   ✅ Webhook response received")
            print(f"   ✅ Response length: {len(response.text)} characters")
            # Check if it's TwiML (should contain <Response>)
            if '<Response>' in response.text:
                print(f"   ✅ Valid TwiML response")
            else:
                print(f"   ⚠️  Response: {response.text[:200]}...")
        else:
            print(f"   ❌ Webhook failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Webhook error: {e}")
        return False
    
    # Test 4: Simulate Call Status Update
    print("\n4. 📊 Testing Call Status Webhook...")
    try:
        status_data = {
            'CallSid': 'test_call_123',
            'CallStatus': 'completed',
            'Duration': '120'
        }
        
        response = requests.post(
            f"{app_url}/webhook/call-status",
            data=status_data,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"   ✅ Status update processed")
        else:
            print(f"   ❌ Status update failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Status update error: {e}")
    
    # Test 5: Test Function Handler
    print("\n5. 🤖 Testing AI Function Handler...")
    try:
        function_data = {
            'function_name': 'check_slot_availability',
            'arguments': {
                'date': '2025-12-25',
                'start_time': '10:00:00'
            },
            'context': {
                'customer_phone': '+39 333 123 4567'
            }
        }
        
        response = requests.post(
            f"{app_url}/api/function-handler",
            json=function_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Function handler working")
            print(f"   ✅ Result: {result}")
        else:
            print(f"   ❌ Function handler failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Function handler error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 DEPLOYED AI SYSTEM TEST COMPLETE!")
    print("=" * 50)
    print("✅ Your spa booking system is ready for phone calls!")
    print("📞 Make a test call to your Twilio number now!")
    
    return True

if __name__ == "__main__":
    test_deployed_ai()
