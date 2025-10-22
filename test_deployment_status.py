#!/usr/bin/env python3
"""
Test deployment status and check what's working
"""

import requests
import time

def test_deployment_status():
    """Test the current deployment status"""
    print("🔍 Testing Deployment Status")
    print("=" * 40)
    
    app_url = "https://spa-booking-system.onrender.com"
    
    # Test 1: Basic health check
    print("1. Basic health check...")
    try:
        response = requests.get(f"{app_url}/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ App is running: {response.json()}")
        else:
            print(f"   ❌ App not responding: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Check if it's the old version or new version
    print("\n2. Checking version...")
    try:
        response = requests.get(f"{app_url}/test-db", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Database test working: {result.get('project_id')}")
        else:
            print(f"   ❌ Database test failed: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Test booking function with different parameter formats
    print("\n3. Testing booking function...")
    try:
        # Test with the old format that should work
        booking_data = {
            'function_name': 'book_spa_slot',
            'arguments': {
                'customer_name': 'Test Customer',
                'customer_phone': '+39 333 123 4567',
                'booking_date': '2025-12-25',
                'start_time': '10:00:00',  # Using start_time instead of slot_start_time
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

if __name__ == "__main__":
    test_deployment_status()
