#!/usr/bin/env python3
"""
Test AI components of the spa booking system
"""

import requests
import json
import sys
import os

# Add backend to path
sys.path.append('backend')

def test_openai_connection():
    """Test OpenAI API connection and assistant creation"""
    print("🤖 Testing OpenAI Connection...")
    
    try:
        from backend.handlers.openai_handler import OpenAIHandler
        handler = OpenAIHandler()
        
        print(f"✅ OpenAI Handler initialized")
        print(f"✅ Assistant ID: {handler.assistant_id}")
        
        # Test creating a thread
        thread = handler.create_thread()
        print(f"✅ Thread created: {thread.id}")
        
        # Test sending a message
        response = handler.send_message(thread.id, "Hello, I want to book a spa appointment")
        print(f"✅ Message sent successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        return False

def test_supabase_functions():
    """Test Supabase database functions"""
    print("\n🗄️ Testing Supabase Functions...")
    
    try:
        from backend.handlers.supabase_handler import SupabaseHandler
        handler = SupabaseHandler()
        
        # Test slot availability
        result = handler.check_slot_availability('2025-12-25', '10:00:00')
        print(f"✅ Slot availability check: {result}")
        
        # Test booking a slot
        booking_result = handler.book_spa_slot({
            'customer_name': 'Test Customer',
            'customer_phone': '+39 333 123 4567',
            'booking_date': '2025-12-25',
            'slot_start_time': '10:00:00',
            'slot_end_time': '12:00:00'
        })
        print(f"✅ Booking test: {booking_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase test failed: {e}")
        return False

def test_twilio_handler():
    """Test Twilio handler initialization"""
    print("\n📞 Testing Twilio Handler...")
    
    try:
        from backend.handlers.twilio_handler import TwilioHandler
        handler = TwilioHandler()
        
        print(f"✅ Twilio Handler initialized")
        
        # Test phone number formatting
        formatted = handler._format_phone_number("+39 333 123 4567")
        print(f"✅ Phone formatting: {formatted}")
        
        return True
        
    except Exception as e:
        print(f"❌ Twilio test failed: {e}")
        return False

def test_app_endpoints():
    """Test app endpoints"""
    print("\n🌐 Testing App Endpoints...")
    
    app_url = "https://spa-booking-system.onrender.com"
    
    try:
        # Test health endpoint
        response = requests.get(f"{app_url}/", timeout=10)
        if response.status_code == 200:
            print(f"✅ Health endpoint: {response.json()}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
            
        # Test database endpoint
        response = requests.get(f"{app_url}/test-db", timeout=10)
        if response.status_code == 200:
            print(f"✅ Database endpoint: {response.json()}")
        else:
            print(f"❌ Database endpoint failed: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ App endpoints test failed: {e}")
        return False

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("\n🔧 Testing Environment Variables...")
    
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN', 
        'TWILIO_PHONE_NUMBER',
        'OPENAI_API_KEY',
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'SUPABASE_SERVICE_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def main():
    """Run all AI component tests"""
    print("🧪 AI Components Test Suite")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("App Endpoints", test_app_endpoints),
        ("Supabase Functions", test_supabase_functions),
        ("Twilio Handler", test_twilio_handler),
        ("OpenAI Connection", test_openai_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Your AI system is ready!")
        print("📞 You can now make a test call to your Twilio number!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        print("🔧 Fix the issues before making a test call.")
    
    return all_passed

if __name__ == "__main__":
    main()
