#!/usr/bin/env python3
"""
Test conversation logging capabilities
Shows what logging will look like during actual calls
"""

import sys
import os
sys.path.append('backend')

from backend.utils.conversation_logger import conversation_logger
from backend.utils.enhanced_logging import (
    log_conversation_turn, 
    log_tool_call, 
    log_call_event, 
    log_booking_event,
    conversation_logger as enhanced_logger
)

def simulate_conversation():
    """Simulate a complete conversation with logging"""
    print("🎭 Simulating Spa Booking Conversation with Enhanced Logging")
    print("=" * 70)
    
    # Simulate call start
    call_sid = "CA1234567890abcdef1234567890abcdef"
    phone_number = "+39 333 123 4567"
    
    print(f"📞 Starting call session: {call_sid}")
    conversation_logger.start_session(call_sid, phone_number)
    
    # Simulate conversation turns
    print("\n💬 Simulating conversation...")
    
    # User: "Hello, I want to book a spa appointment"
    conversation_logger.log_user_input(
        call_sid, 
        "Hello, I want to book a spa appointment",
        audio_duration=3.2,
        confidence=0.95
    )
    
    # Assistant: "Hello! I'd be happy to help you book a spa appointment..."
    conversation_logger.log_assistant_response(
        call_sid,
        "Hello! I'd be happy to help you book a spa appointment. What's your name?",
        processing_time=1.8
    )
    
    # User: "My name is Maria"
    conversation_logger.log_user_input(
        call_sid,
        "My name is Maria",
        audio_duration=2.1,
        confidence=0.98
    )
    
    # Assistant: "Nice to meet you Maria! When would you like to book your appointment?"
    conversation_logger.log_assistant_response(
        call_sid,
        "Nice to meet you Maria! When would you like to book your appointment?",
        processing_time=1.5
    )
    
    # User: "Tomorrow at 10 AM"
    conversation_logger.log_user_input(
        call_sid,
        "Tomorrow at 10 AM",
        audio_duration=2.8,
        confidence=0.92
    )
    
    # Tool call: Check availability
    conversation_logger.log_tool_call(
        call_sid,
        "check_slot_availability",
        {"date": "2025-10-22", "start_time": "10:00:00"},
        {"available": True, "spots_remaining": 12},
        True,
        0.3
    )
    
    # Assistant: "Great! I have availability tomorrow at 10 AM..."
    conversation_logger.log_assistant_response(
        call_sid,
        "Great! I have availability tomorrow at 10 AM. I'll book that for you now.",
        processing_time=2.1
    )
    
    # Tool call: Book appointment
    conversation_logger.log_tool_call(
        call_sid,
        "book_spa_slot",
        {
            "customer_name": "Maria",
            "customer_phone": "+39 333 123 4567",
            "booking_date": "2025-10-22",
            "slot_start_time": "10:00:00",
            "slot_end_time": "12:00:00"
        },
        {
            "status": "success",
            "booking_id": "SPA-000123",
            "booking_reference": "SPA-000123"
        },
        True,
        0.8
    )
    
    # Log booking creation
    conversation_logger.log_booking_created(call_sid, "SPA-000123")
    
    # Assistant: "Perfect! Your appointment is confirmed..."
    conversation_logger.log_assistant_response(
        call_sid,
        "Perfect! Your appointment is confirmed for tomorrow at 10 AM. You'll receive an SMS confirmation shortly.",
        processing_time=1.9
    )
    
    # User: "Thank you!"
    conversation_logger.log_user_input(
        call_sid,
        "Thank you!",
        audio_duration=1.5,
        confidence=0.99
    )
    
    # Assistant: "You're welcome! Have a great day!"
    conversation_logger.log_assistant_response(
        call_sid,
        "You're welcome! Have a great day!",
        processing_time=1.2
    )
    
    # End call
    print(f"\n📞 Ending call session: {call_sid}")
    conversation_logger.end_session(call_sid, "completed")
    
    print("\n" + "=" * 70)
    print("🎉 Conversation simulation complete!")
    print("📊 Check the logs/conversations.log file for detailed logging")
    print("📈 This is the same level of logging you'll get with ElevenLabs!")

def show_logging_capabilities():
    """Show what logging capabilities are available"""
    print("\n🔍 ENHANCED LOGGING CAPABILITIES:")
    print("=" * 50)
    
    capabilities = [
        "📞 Call session tracking (start, duration, end)",
        "👤 User speech transcription with confidence scores",
        "🤖 AI assistant responses with processing times",
        "🔧 Tool/function calls with arguments and results",
        "📝 Booking creation and confirmation events",
        "📊 Conversation analytics and metrics",
        "💾 Persistent storage for conversation history",
        "📈 Real-time monitoring and debugging",
        "🎯 Call quality and success rate tracking",
        "📱 SMS confirmation delivery tracking"
    ]
    
    for capability in capabilities:
        print(f"   {capability}")
    
    print(f"\n📁 Log files created:")
    print(f"   - logs/conversations.log (detailed conversation logs)")
    print(f"   - Console output (real-time monitoring)")
    print(f"   - Supabase database (analytics storage)")

if __name__ == "__main__":
    simulate_conversation()
    show_logging_capabilities()
