#!/usr/bin/env python3
"""
Test different parameter mappings to find the correct format
"""

import requests
import json

def test_parameter_mapping():
    """Test different parameter mappings"""
    print("🔧 Testing Parameter Mapping")
    print("=" * 40)
    
    app_url = "https://spa-booking-system.onrender.com"
    
    # Test 1: Using 'name' instead of 'customer_name'
    print("1. Testing with 'name' parameter...")
    try:
        booking_data = {
            'function_name': 'book_spa_slot',
            'arguments': {
                'name': 'Test Customer',  # Using 'name' instead of 'customer_name'
                'phone': '+39 333 123 4567',  # Using 'phone' instead of 'customer_phone'
                'date': '2025-12-25',  # Using 'date' instead of 'booking_date'
                'start_time': '10:00:00',
                'end_time': '12:00:00'
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
            print(f"   ❌ Request failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Using mixed parameters
    print("\n2. Testing with mixed parameters...")
    try:
        booking_data = {
            'function_name': 'book_spa_slot',
            'arguments': {
                'customer_name': 'Test Customer 2',
                'customer_phone': '+39 333 123 4568',
                'booking_date': '2025-12-26',
                'slot_start_time': '14:00:00',
                'slot_end_time': '16:00:00'
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
            print(f"   ❌ Request failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_parameter_mapping()
