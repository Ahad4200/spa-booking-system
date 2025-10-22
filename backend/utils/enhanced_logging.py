"""
Enhanced logging configuration for production-grade conversation tracking
Similar to ElevenLabs conversation analytics
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any

class ConversationFormatter(logging.Formatter):
    """Custom formatter for conversation logs"""
    
    def format(self, record):
        # Add emoji prefixes for different log types
        if hasattr(record, 'conversation_type'):
            if record.conversation_type == 'user_input':
                record.msg = f"👤 USER: {record.msg}"
            elif record.conversation_type == 'assistant_response':
                record.msg = f"🤖 ASSISTANT: {record.msg}"
            elif record.conversation_type == 'tool_call':
                record.msg = f"🔧 TOOL: {record.msg}"
            elif record.conversation_type == 'call_event':
                record.msg = f"📞 CALL: {record.msg}"
            elif record.conversation_type == 'booking_event':
                record.msg = f"📝 BOOKING: {record.msg}"
        
        return super().format(record)

def setup_enhanced_logging():
    """Setup enhanced logging for conversation tracking"""
    
    # Create conversation logger
    conversation_logger = logging.getLogger('conversation')
    conversation_logger.setLevel(logging.INFO)
    
    # Create file handler for conversation logs
    conversation_handler = logging.FileHandler('logs/conversations.log')
    conversation_handler.setLevel(logging.INFO)
    
    # Create console handler for real-time monitoring
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Set custom formatter
    formatter = ConversationFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    conversation_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    conversation_logger.addHandler(conversation_handler)
    conversation_logger.addHandler(console_handler)
    
    return conversation_logger

def log_conversation_turn(logger, call_sid: str, speaker: str, text: str, **kwargs):
    """Log a conversation turn with metadata"""
    metadata = {
        'call_sid': call_sid,
        'speaker': speaker,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    conversation_type = 'user_input' if speaker == 'user' else 'assistant_response'
    
    logger.info(
        f"{text}",
        extra={
            'conversation_type': conversation_type,
            'metadata': metadata
        }
    )

def log_tool_call(logger, call_sid: str, function_name: str, arguments: Dict, result: Dict, success: bool, execution_time: float):
    """Log tool/function calls with full details"""
    metadata = {
        'call_sid': call_sid,
        'function_name': function_name,
        'arguments': arguments,
        'result': result,
        'success': success,
        'execution_time': execution_time,
        'timestamp': datetime.now().isoformat()
    }
    
    status = "SUCCESS" if success else "FAILED"
    logger.info(
        f"{function_name} - {status} ({execution_time:.2f}s)",
        extra={
            'conversation_type': 'tool_call',
            'metadata': metadata
        }
    )

def log_call_event(logger, call_sid: str, event_type: str, details: Dict):
    """Log call events (start, end, status changes)"""
    metadata = {
        'call_sid': call_sid,
        'event_type': event_type,
        'timestamp': datetime.now().isoformat(),
        **details
    }
    
    logger.info(
        f"{event_type.upper()}: {json.dumps(details)}",
        extra={
            'conversation_type': 'call_event',
            'metadata': metadata
        }
    )

def log_booking_event(logger, call_sid: str, event_type: str, booking_data: Dict):
    """Log booking-related events"""
    metadata = {
        'call_sid': call_sid,
        'event_type': event_type,
        'timestamp': datetime.now().isoformat(),
        **booking_data
    }
    
    logger.info(
        f"{event_type.upper()}: {json.dumps(booking_data)}",
        extra={
            'conversation_type': 'booking_event',
            'metadata': metadata
        }
    )

# Create logs directory if it doesn't exist
import os
os.makedirs('logs', exist_ok=True)

# Setup enhanced logging
conversation_logger = setup_enhanced_logging()
