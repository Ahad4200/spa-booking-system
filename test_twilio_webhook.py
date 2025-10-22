#!/usr/bin/env python3
"""
Test Twilio webhook responses in detail
"""

import requests
import json
from xml.etree import ElementTree as ET

def test_twilio_webhook_detailed():
    """Test Twilio webhook with detailed analysis"""
    print("📞 Testing Twilio Webhook in Detail")
    print("=" * 50)
    
    app_url = "https://spa-booking-system.onrender.com"
    
    # Test incoming call webhook
    print("1. Testing Incoming Call Webhook...")
    
    webhook_data = {
        'CallSid': 'CA1234567890abcdef1234567890abcdef',
        'From': '+39 333 123 4567',
        'To': '+39 333 987 6543',
        'CallStatus': 'ringing',
        'FromCountry': 'IT',
        'ToCountry': 'IT'
    }
    
    try:
        response = requests.post(
            f"{app_url}/webhook/incoming-call",
            data=webhook_data,
            timeout=15
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Content Type: {response.headers.get('content-type', 'unknown')}")
        print(f"   Response Length: {len(response.text)} characters")
        
        if response.status_code == 200:
            print("   ✅ Webhook successful")
            
            # Parse TwiML response
            try:
                root = ET.fromstring(response.text)
                print("   ✅ Valid TwiML XML")
                
                # Analyze TwiML structure
                print("\n   📋 TwiML Analysis:")
                for elem in root:
                    print(f"      - {elem.tag}: {elem.text[:50]}..." if elem.text else f"      - {elem.tag}")
                    
                    # Check for WebSocket connection
                    if elem.tag == 'Connect':
                        for child in elem:
                            if child.tag == 'Stream':
                                url = child.get('url', '')
                                if 'openai.com' in url:
                                    print(f"         ✅ OpenAI WebSocket URL found")
                                    print(f"         URL: {url}")
                                else:
                                    print(f"         ❌ Unexpected WebSocket URL: {url}")
                    
                    # Check for Say element
                    if elem.tag == 'Say':
                        voice = elem.get('voice', 'default')
                        language = elem.get('language', 'default')
                        print(f"         Voice: {voice}, Language: {language}")
                        print(f"         Message: {elem.text}")
                        
            except ET.ParseError as e:
                print(f"   ❌ Invalid TwiML XML: {e}")
                print(f"   Raw response: {response.text}")
        else:
            print(f"   ❌ Webhook failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Webhook error: {e}")
    
    # Test call status webhook
    print("\n2. Testing Call Status Webhook...")
    
    status_data = {
        'CallSid': 'CA1234567890abcdef1234567890abcdef',
        'CallStatus': 'completed',
        'Duration': '120',
        'From': '+39 333 123 4567',
        'To': '+39 333 987 6543'
    }
    
    try:
        response = requests.post(
            f"{app_url}/webhook/call-status",
            data=status_data,
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Status webhook successful")
        else:
            print(f"   ❌ Status webhook failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Status webhook error: {e}")
    
    # Test function handler with different scenarios
    print("\n3. Testing AI Function Handler...")
    
    test_scenarios = [
        {
            'name': 'Check Availability',
            'data': {
                'function_name': 'check_slot_availability',
                'arguments': {
                    'date': '2025-12-25',
                    'start_time': '10:00:00'
                },
                'context': {
                    'customer_phone': '+39 333 123 4567'
                }
            }
        },
        {
            'name': 'Book Appointment',
            'data': {
                'function_name': 'book_spa_slot',
                'arguments': {
                    'customer_name': 'Test Customer',
                    'customer_phone': '+39 333 123 4567',
                    'booking_date': '2025-12-25',
                    'slot_start_time': '10:00:00',
                    'slot_end_time': '12:00:00'
                },
                'context': {
                    'customer_phone': '+39 333 123 4567'
                }
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n   Testing: {scenario['name']}")
        try:
            response = requests.post(
                f"{app_url}/api/function-handler",
                json=scenario['data'],
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"      ✅ Success: {result}")
            else:
                print(f"      ❌ Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Twilio Webhook Testing Complete!")

if __name__ == "__main__":
    test_twilio_webhook_detailed()
