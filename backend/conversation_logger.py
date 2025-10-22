"""
Enhanced conversation logging for spa booking system
Similar to ElevenLabs conversation tracking
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    timestamp: str
    speaker: str  # 'user' or 'assistant'
    text: str
    audio_duration: Optional[float] = None
    processing_time: Optional[float] = None
    confidence: Optional[float] = None

@dataclass
class ToolCall:
    """Tool/function call during conversation"""
    timestamp: str
    function_name: str
    arguments: Dict
    result: Dict
    success: bool
    execution_time: float

@dataclass
class CallSession:
    """Complete call session with conversation"""
    call_sid: str
    phone_number: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[float] = None
    conversation_turns: List[ConversationTurn] = None
    tool_calls: List[ToolCall] = None
    booking_created: bool = False
    booking_id: Optional[str] = None
    final_status: str = "in_progress"

class ConversationLogger:
    """Enhanced logging for conversation tracking"""
    
    def __init__(self):
        self.logger = logging.getLogger('conversation')
        self.sessions: Dict[str, CallSession] = {}
    
    def start_session(self, call_sid: str, phone_number: str) -> CallSession:
        """Start tracking a new call session"""
        session = CallSession(
            call_sid=call_sid,
            phone_number=phone_number,
            start_time=datetime.now().isoformat(),
            conversation_turns=[],
            tool_calls=[]
        )
        self.sessions[call_sid] = session
        
        self.logger.info(f"📞 Call session started: {call_sid} from {phone_number}")
        return session
    
    def log_user_input(self, call_sid: str, text: str, audio_duration: float = None, confidence: float = None):
        """Log user speech input"""
        if call_sid not in self.sessions:
            self.start_session(call_sid, "unknown")
        
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            speaker="user",
            text=text,
            audio_duration=audio_duration,
            confidence=confidence
        )
        
        self.sessions[call_sid].conversation_turns.append(turn)
        
        self.logger.info(f"👤 User said: '{text}' (confidence: {confidence}, duration: {audio_duration}s)")
    
    def log_assistant_response(self, call_sid: str, text: str, processing_time: float = None):
        """Log AI assistant response"""
        if call_sid not in self.sessions:
            return
        
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            speaker="assistant",
            text=text,
            processing_time=processing_time
        )
        
        self.sessions[call_sid].conversation_turns.append(turn)
        
        self.logger.info(f"🤖 Assistant: '{text}' (processing: {processing_time}s)")
    
    def log_tool_call(self, call_sid: str, function_name: str, arguments: Dict, result: Dict, success: bool, execution_time: float):
        """Log tool/function calls"""
        if call_sid not in self.sessions:
            return
        
        tool_call = ToolCall(
            timestamp=datetime.now().isoformat(),
            function_name=function_name,
            arguments=arguments,
            result=result,
            success=success,
            execution_time=execution_time
        )
        
        self.sessions[call_sid].tool_calls.append(tool_call)
        
        status = "✅" if success else "❌"
        self.logger.info(f"🔧 Tool call: {function_name} {status} ({execution_time:.2f}s)")
        self.logger.info(f"   Arguments: {json.dumps(arguments, indent=2)}")
        self.logger.info(f"   Result: {json.dumps(result, indent=2)}")
    
    def log_booking_created(self, call_sid: str, booking_id: str):
        """Log successful booking creation"""
        if call_sid in self.sessions:
            self.sessions[call_sid].booking_created = True
            self.sessions[call_sid].booking_id = booking_id
            
            self.logger.info(f"📝 Booking created: {booking_id} for call {call_sid}")
    
    def end_session(self, call_sid: str, status: str = "completed"):
        """End call session and log summary"""
        if call_sid not in self.sessions:
            return
        
        session = self.sessions[call_sid]
        session.end_time = datetime.now().isoformat()
        session.final_status = status
        
        # Calculate duration
        start = datetime.fromisoformat(session.start_time)
        end = datetime.fromisoformat(session.end_time)
        session.duration = (end - start).total_seconds()
        
        # Log session summary
        self.logger.info(f"📊 Call session ended: {call_sid}")
        self.logger.info(f"   Duration: {session.duration:.1f}s")
        self.logger.info(f"   Turns: {len(session.conversation_turns)}")
        self.logger.info(f"   Tool calls: {len(session.tool_calls)}")
        self.logger.info(f"   Booking created: {session.booking_created}")
        self.logger.info(f"   Status: {status}")
        
        # Log full conversation
        self.logger.info("💬 Full conversation:")
        for turn in session.conversation_turns:
            speaker_emoji = "👤" if turn.speaker == "user" else "🤖"
            self.logger.info(f"   {speaker_emoji} {turn.speaker}: {turn.text}")
        
        # Store in database for analytics
        self._store_session_analytics(session)
    
    def _store_session_analytics(self, session: CallSession):
        """Store session data for analytics"""
        try:
            # This would store in Supabase for analytics
            analytics_data = {
                "call_sid": session.call_sid,
                "phone_number": session.phone_number,
                "duration": session.duration,
                "turns_count": len(session.conversation_turns),
                "tool_calls_count": len(session.tool_calls),
                "booking_created": session.booking_created,
                "booking_id": session.booking_id,
                "conversation_transcript": [
                    {
                        "speaker": turn.speaker,
                        "text": turn.text,
                        "timestamp": turn.timestamp,
                        "audio_duration": turn.audio_duration,
                        "confidence": turn.confidence
                    }
                    for turn in session.conversation_turns
                ],
                "tool_calls": [
                    {
                        "function_name": call.function_name,
                        "arguments": call.arguments,
                        "result": call.result,
                        "success": call.success,
                        "execution_time": call.execution_time,
                        "timestamp": call.timestamp
                    }
                    for call in session.tool_calls
                ]
            }
            
            self.logger.info(f"📈 Analytics data prepared for call {session.call_sid}")
            # TODO: Store in Supabase analytics table
            
        except Exception as e:
            self.logger.error(f"Failed to store analytics: {e}")

# Global conversation logger instance
conversation_logger = ConversationLogger()
