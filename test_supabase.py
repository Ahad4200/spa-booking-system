#!/usr/bin/env python3
"""
Test Supabase connection from your deployed app
"""

import requests
import json

def test_supabase_connection():
    """Test if Supabase is reachable from your deployed app"""
    
    # Your deployed app URL
    app_url = "https://spa-booking-system.onrender.com"
    
    print("🔍 Testing Supabase connection...")
    print(f"App URL: {app_url}")
    
    try:
        # Test 1: Basic health check
        print("\n1. Testing basic health check...")
        response = requests.get(f"{app_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ App is running")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ App health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach app: {e}")
        return False
    
    try:
        # Test 2: Database connection (if you add the test endpoint)
        print("\n2. Testing database connection...")
        response = requests.get(f"{app_url}/test-db", timeout=10)
        if response.status_code == 200:
            print("✅ Database connection successful")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Database test failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Database test error: {e}")
    
    print("\n🎯 Manual Test:")
    print(f"Visit: {app_url}/")
    print("You should see: {'status': 'healthy', 'service': 'Spa Booking System', 'version': '1.0.0'}")

if __name__ == "__main__":
    test_supabase_connection()
