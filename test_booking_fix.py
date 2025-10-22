#!/usr/bin/env python3
"""
Test the booking function fix specifically
"""

import requests
import json

def test_booking_function():
    """Test the booking function with different parameter formats"""
    print("🔧 Testing Booking Function Fix")
    print("=" * 40)
    
    app_url = "https://spa-booking-system.onrender.com"
    
    # Test 1: With slot_start_time format
    print("1. Testing with slot_start_time format...")
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
    
    # Test 2: With start_time format
    print("\n2. Testing with start_time format...")
    try:
        booking_data = {
            'function_name': 'book_spa_slot',
            'arguments': {
                'customer_name': 'Test Customer 2',
                'customer_phone': '+39 333 123 4568',
                'booking_date': '2025-12-26',
                'start_time': '14:00:00',
                'end_time': '16:00:00'
            },
            'context': {
                'customer_phone': '+39 333 123 4568'
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
    
    # Test 3: Check availability first
    print("\n3. Testing availability check...")
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
            print(f"   Result: {result}")
        else:
            print(f"   ❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_booking_function()
