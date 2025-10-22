#!/usr/bin/env python3
"""
Test import without configuration validation
"""

import os
import sys

# Set dummy environment variables to bypass validation
os.environ['TWILIO_ACCOUNT_SID'] = 'dummy'
os.environ['TWILIO_AUTH_TOKEN'] = 'dummy'
os.environ['OPENAI_API_KEY'] = 'dummy'
os.environ['SUPABASE_URL'] = 'dummy'
os.environ['SUPABASE_KEY'] = 'dummy'

# Add backend to path
sys.path.append('backend')

try:
    from backend.app import app
    print("✅ App import successful!")
except Exception as e:
    print(f"❌ App import failed: {e}")
    import traceback
    traceback.print_exc()
