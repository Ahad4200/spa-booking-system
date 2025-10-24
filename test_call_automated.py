# test_call_automated.py
from twilio.rest import Client
import os
import time
import sys

try:
    client = Client(
        os.environ.get('TWILIO_ACCOUNT_SID'),
        os.environ.get('TWILIO_AUTH_TOKEN')
    )
except Exception as e:
    print(f"❌ Failed to initialize Twilio client: {e}")
    print("Ensure TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are set")
    sys.exit(1)

# Replace with your actual phone number
YOUR_PHONE = "+923195976571"  # ⚠️ UPDATE THIS WITH YOUR ACTUAL PHONE NUMBER
TWILIO_NUMBER = "+13412175012"
WEBHOOK_URL = "https://spa-booking-system.onrender.com/webhook/incoming-call"

print("\n" + "="*60)
print("🚀 INITIATING AUTOMATED TEST CALL")
print("="*60)
print(f"📞 Calling: {YOUR_PHONE}")
print(f"📡 From: {TWILIO_NUMBER}")
print(f"🌐 Webhook: {WEBHOOK_URL}")
print("\n⏳ WAITING FOR CALL TO RING...")
print("📢 IMPORTANT: Answer the call and say:")
print("   'Hello, I want to book a massage for tomorrow at 3pm'")
print("\n(Or any natural sentence in Italian or English)")
print("="*60 + "\n")

try:
    call = client.calls.create(
        to=YOUR_PHONE,
        from_=TWILIO_NUMBER,
        url=WEBHOOK_URL
    )
    print(f"✅ Call initiated successfully!")
    print(f"📋 Call SID: {call.sid}\n")
    
except Exception as e:
    print(f"❌ Failed to create call: {e}")
    sys.exit(1)

# Wait for call to complete (max 35 seconds)
print("⏱️  Waiting 35 seconds for call to complete...")
time.sleep(35)

try:
    call = client.calls(call.sid).fetch()
    
    print("\n" + "="*60)
    print("📊 CALL RESULTS")
    print("="*60)
    print(f"Call SID: {call.sid}")
    print(f"Status: {call.status}")
    print(f"Duration: {call.duration} seconds")
    print(f"Price: ${call.price if call.price else '0.00'}")
    print("="*60)
    
    # Analysis
    duration = int(call.duration) if call.duration else 0
    
    if duration < 5:
        print("❌ FAILURE: Call too short (< 5 seconds)")
        print("   Likely cause: WebSocket connection not established or immediate disconnect")
        print("   Action: aCheck /media-stream WebSocket handler logs")
        
    elif duration >= 5 and duration < 15:
        print("⚠️  PARTIAL: Call lasted but might be incomplete")
        print(f"   Duration: {duration} seconds")
        print("   Likely cause: AI responded but conversation incomplete or connection dropped")
        print("   Action: Check Render logs for WebSocket errors or OpenAI timeout")
        
    elif duration >= 15:
        print("✅ SUCCESS: Full conversation duration achieved!")
        print("   Did you hear the AI respond naturally? If YES, the integration works!")
        print("   If NO AI response but call was long: Check speaker volume or audio encoding")
        
    else:
        print("⚠️  UNKNOWN: Could not determine call status")
        
except Exception as e:
    print(f"❌ Failed to fetch call status: {e}")
    print(f"📋 Call SID: {call.sid}")
    print("Check Twilio Console for details: https://console.twilio.com/us1/monitor/calls")
