#!/usr/bin/env python3
"""
Comprehensive test suite for the spa booking system
Tests all components before live call
"""

import requests
import json
import time
from datetime import datetime, timedelta

def test_deployment():
    base_url = "https://spa-booking-system.onrender.com"
    
    print("🧪 COMPREHENSIVE SPA BOOKING SYSTEM TEST")
    print("=" * 60)
    print(f"Testing URL: {base_url}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test 1: Basic Connectivity
    print("\n1. 🌐 BASIC CONNECTIVITY TEST")
    try:
        response = requests.get(f"{base_url}/", timeout=15)
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 404]:  # 404 is OK for root
            print("   ✅ Server is responding")
        else:
            print(f"   ❌ Server error: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # Test 2: Webhook with Real Twilio Data
    print("\n2. 📞 TWILIO WEBHOOK TEST")
    try:
        # Simulate real Twilio webhook data
        webhook_data = {
            "From": "+1234567890",
            "To": "+13412175012",
            "CallSid": "CA1234567890abcdef1234567890abcdef",
            "Direction": "inbound",
            "CallStatus": "ringing",
            "FromCity": "New York",
            "FromState": "NY",
            "FromCountry": "US",
            "ToCity": "Miami",
            "ToState": "FL",
            "ToCountry": "US"
        }
        
        response = requests.post(f"{base_url}/webhook/incoming-call", 
                               data=webhook_data, timeout=15)
        print(f"   Status: {response.status_code}")
        print(f"   Response Length: {len(response.text)} chars")
        
        if response.status_code == 200:
            if "<?xml" in response.text and "Response" in response.text:
                print("   ✅ Valid TwiML response received")
                if "Stream" in response.text:
                    print("   ✅ Media Stream configured")
                else:
                    print("   ⚠️  No Media Stream found in TwiML")
            else:
                print(f"   ❌ Invalid TwiML: {response.text[:200]}")
        else:
            print(f"   ❌ Webhook failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Webhook test error: {e}")
    
    # Test 3: Database Functions
    print("\n3. 🗄️ DATABASE CONNECTION TEST")
    try:
        # Test slot availability
        function_data = {
            "function_name": "check_slot_availability",
            "arguments": {
                "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                "start_time": "10:00"
            },
            "context": {
                "from": "+1234567890"
            }
        }
        
        response = requests.post(f"{base_url}/api/function-handler", 
                               json=function_data, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Database connected: {result}")
        else:
            print(f"   ❌ Database error: {response.text}")
    except Exception as e:
        print(f"   ❌ Database test error: {e}")
    
    # Test 4: Booking Function
    print("\n4. 📅 BOOKING FUNCTION TEST")
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        function_data = {
            "function_name": "book_spa_slot",
            "arguments": {
                "name": "Test Customer",
                "date": tomorrow,
                "start_time": "10:00",
                "end_time": "12:00"
            },
            "context": {
                "from": "+1234567890"
            }
        }
        
        response = requests.post(f"{base_url}/api/function-handler", 
                               json=function_data, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Booking function working: {result}")
        else:
            print(f"   ❌ Booking error: {response.text}")
    except Exception as e:
        print(f"   ❌ Booking test error: {e}")
    
    # Test 5: Appointment Management
    print("\n5. 📋 APPOINTMENT MANAGEMENT TEST")
    try:
        # Test get_latest_appointment
        function_data = {
            "function_name": "get_latest_appointment",
            "arguments": {
                "phone_number": "+1234567890"
            },
            "context": {
                "from": "+1234567890"
            }
        }
        
        response = requests.post(f"{base_url}/api/function-handler", 
                               json=function_data, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Appointment lookup working: {result}")
        else:
            print(f"   ❌ Appointment lookup error: {response.text}")
    except Exception as e:
        print(f"   ❌ Appointment test error: {e}")
    
    # Test 6: WebSocket Endpoint
    print("\n6. 🔌 WEBSOCKET ENDPOINT TEST")
    try:
        # Test if WebSocket endpoint is accessible
        response = requests.get(f"{base_url}/media-stream", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:  # Expected for WebSocket upgrade
            print("   ✅ WebSocket endpoint accessible")
        elif response.status_code == 404:
            print("   ❌ WebSocket endpoint not found")
        else:
            print(f"   ⚠️  Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"   ❌ WebSocket test error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 COMPREHENSIVE TEST COMPLETED")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_deployment()
