#!/usr/bin/env python3
"""
Test the current deployed version to see what's working
"""

import requests
import json

def test_current_version():
    """Test the current deployed version"""
    print("🔍 Testing Current Deployed Version")
    print("=" * 40)
    
    app_url = "https://spa-booking-system.onrender.com"
    
    # Test 1: Health check
    print("1. Health check...")
    try:
        response = requests.get(f"{app_url}/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ App is healthy: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Database connectivity
    print("\n2. Database connectivity...")
    try:
        response = requests.get(f"{app_url}/test-db", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Database connected: {result.get('project_id')}")
        else:
            print(f"   ❌ Database test failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Booking function with current parameter format
    print("\n3. Testing booking function...")
    try:
        booking_data = {
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
        
        response = requests.post(
            f"{app_url}/api/function-handler",
            json=booking_data,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Result: {result}")
            if result.get('success'):
                print("   ✅ Booking successful!")
            else:
                print(f"   ❌ Booking failed: {result.get('error')}")
        else:
            print(f"   ❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Availability check
    print("\n4. Testing availability check...")
    try:
        availability_data = {
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
            json=availability_data,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Availability check: {result}")
        else:
            print(f"   ❌ Availability check failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_current_version()
