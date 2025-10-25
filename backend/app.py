"""
Spa Booking System - Production Ready with Conversation Logging & Tool Calling
Complete implementation with ElevenLabs-style conversation tracking
"""

import asyncio
import base64
import json
import os
import time
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import quote
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Form
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import websockets
from dotenv import load_dotenv
from supabase import create_client, Client
from dataclasses import dataclass, field, asdict

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Spa Booking System", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration class
class Config:
    SPA_NAME = os.getenv("SPA_NAME", "Santa Caterina Beauty Farm")
    SESSION_DURATION_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "2"))
    MAX_CAPACITY_PER_SLOT = int(os.getenv("MAX_CAPACITY_PER_SLOT", "14"))
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE = os.getenv("VOICE", "alloy")
OPENAI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME", "spa-booking-system.onrender.com")

# Validate critical environment variables
if not OPENAI_API_KEY:
    logger.error("❌ OPENAI_API_KEY not found!")
    raise ValueError("OPENAI_API_KEY is required")

if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
    logger.error("❌ SUPABASE configuration missing!")
    raise ValueError("Supabase configuration is required")

# Initialize Supabase client
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
logger.info(f"✅ Connected to Supabase at {Config.SUPABASE_URL}")

# ============================================
#         CONVERSATION LOGGING CLASSES
# ============================================

@dataclass
class ConversationTurn:
    """Represents one turn in the conversation"""
    timestamp: str
    role: str  # "user" or "assistant"
    transcript: str
    turn_number: int = 0
    audio_duration_ms: Optional[int] = None
    event_id: Optional[str] = None
    item_id: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FunctionCall:
    """Represents a function call in the conversation"""
    timestamp: str
    function_name: str
    arguments: Dict[str, Any]
    call_id: str
    result: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

@dataclass
class ConversationLog:
    """Complete conversation record"""
    conversation_id: str
    customer_phone: str
    call_sid: str
    stream_sid: str
    started_at: str
    db_id: Optional[str] = None  # UUID from database
    ended_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    model_used: str = OPENAI_MODEL
    turns: list[ConversationTurn] = field(default_factory=list)
    function_calls: list[FunctionCall] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    turn_counter: int = 0

class ConversationLogger:
    """Manages conversation logging to Supabase"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.conversations: Dict[str, ConversationLog] = {}
    
    def create_conversation(self, log: ConversationLog) -> str:
        """Create new conversation record in database"""
        try:
            # Insert into conversations table
            result = self.supabase.table('conversations').insert({
                'conversation_id': log.conversation_id,
                'customer_phone': log.customer_phone,
                'call_sid': log.call_sid,
                'stream_sid': log.stream_sid,
                'started_at': log.started_at,
                'model_used': log.model_used,
                'metadata': log.metadata
            }).execute()
            
            db_id = result.data[0]['id']
            log.db_id = db_id
            self.conversations[log.conversation_id] = log
            
            logger.info(f"📝 Created conversation log: {db_id}")
            return db_id
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return None
    
    def add_turn(self, conversation_id: str, turn: ConversationTurn):
        """Add a conversation turn to database"""
        try:
            if conversation_id not in self.conversations:
                logger.warning(f"Conversation {conversation_id} not found")
                return
            
            log = self.conversations[conversation_id]
            log.turn_counter += 1
            turn.turn_number = log.turn_counter
            log.turns.append(turn)
            
            # Insert into database
            self.supabase.table('conversation_turns').insert({
                'conversation_id': log.db_id,
                'turn_number': turn.turn_number,
                'timestamp': turn.timestamp,
                'role': turn.role,
                'transcript': turn.transcript,
                'audio_duration_ms': turn.audio_duration_ms,
                'event_id': turn.event_id,
                'item_id': turn.item_id,
                'confidence_score': turn.confidence_score,
                'metadata': turn.metadata
            }).execute()
            
            # Update turn count
            self.supabase.table('conversations').update({
                'total_turns': log.turn_counter
            }).eq('id', log.db_id).execute()
            
            logger.info(f"💬 Turn #{turn.turn_number} ({turn.role}): {turn.transcript[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to add turn: {e}")
    
    def add_function_call(self, conversation_id: str, function_call: FunctionCall):
        """Log function call to database"""
        try:
            if conversation_id not in self.conversations:
                return
            
            log = self.conversations[conversation_id]
            log.function_calls.append(function_call)
            
            # Calculate execution time if we have result
            execution_time = None
            if function_call.result:
                start = datetime.fromisoformat(function_call.timestamp)
                execution_time = int((datetime.now() - start).total_seconds() * 1000)
                function_call.execution_time_ms = execution_time
            
            # Insert into database
            self.supabase.table('function_calls').insert({
                'conversation_id': log.db_id,
                'timestamp': function_call.timestamp,
                'function_name': function_call.function_name,
                'arguments': function_call.arguments,
                'result': function_call.result,
                'success': function_call.success,
                'error_message': function_call.error_message,
                'execution_time_ms': execution_time,
                'call_id': function_call.call_id
            }).execute()
            
            # Update function call count
            self.supabase.table('conversations').update({
                'total_functions_called': len(log.function_calls)
            }).eq('id', log.db_id).execute()
            
            logger.info(f"🔧 Logged function: {function_call.function_name} (success: {function_call.success})")
            
        except Exception as e:
            logger.error(f"Failed to log function call: {e}")
    
    def end_conversation(self, conversation_id: str):
        """Mark conversation as ended"""
        try:
            if conversation_id not in self.conversations:
                return
            
            log = self.conversations[conversation_id]
            log.ended_at = datetime.now().isoformat()
            
            # Calculate duration
            start = datetime.fromisoformat(log.started_at)
            end = datetime.fromisoformat(log.ended_at)
            duration = int((end - start).total_seconds())
            log.duration_seconds = duration
            
            # Update database
            self.supabase.table('conversations').update({
                'ended_at': log.ended_at,
                'duration_seconds': duration
            }).eq('id', log.db_id).execute()
            
            logger.info(f"📞 Conversation ended: {conversation_id} (duration: {duration}s)")
            
            # Clean up memory
            del self.conversations[conversation_id]
            
        except Exception as e:
            logger.error(f"Failed to end conversation: {e}")

# Global conversation logger instance
conversation_logger = ConversationLogger(supabase)

# ============================================
#              HELPER FUNCTIONS
# ============================================

def format_time_for_db(time_str: str) -> str:
    """Convert HH:MM to HH:MM:SS for database TIME field"""
    if time_str and len(time_str) == 5:
        return f"{time_str}:00"
    return time_str

def calculate_end_time(start_time: str) -> str:
    """Calculate end time based on 2-hour session duration"""
    try:
        hour, minute = map(int, start_time.split(':')[:2])
        end_hour = hour + Config.SESSION_DURATION_HOURS
        return f"{end_hour:02d}:{minute:02d}:00"
    except:
        return "12:00:00"

def get_system_message(caller_phone):
    """Generate system message with actual values"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return f"""# Role
You are Sara, a warm and professional AI receptionist for {Config.SPA_NAME}, a luxury wellness spa in Italy.

# Context
- Current date/time: {current_time}
- Caller's phone: {caller_phone} (automatically provided - NEVER ask for it)
- Operating hours: Monday-Saturday 10:00-20:00, Sunday CLOSED
- Session duration: {Config.SESSION_DURATION_HOURS} hours per slot
- Maximum capacity: {Config.MAX_CAPACITY_PER_SLOT} people per time slot
- Available slots: 10:00-12:00, 12:00-14:00, 14:00-16:00, 16:00-18:00, 18:00-20:00

# Conversation Flows

## NEW BOOKING Flow
1. Greet warmly in Italian or English
2. Ask for name
3. Ask for preferred date
4. Ask for preferred time
5. Check availability using check_slot_availability function
6. If available, book using book_spa_slot function
7. Confirm with booking reference

## CHECK APPOINTMENT Flow
1. Use get_latest_appointment function immediately
2. Read appointment details if found
3. Offer to help with changes if needed

## CANCELLATION Flow
1. Use get_latest_appointment to find booking
2. Confirm details with customer
3. Upon confirmation, use delete_appointment function
4. Confirm cancellation

# Important
- Be warm and professional
- Speak naturally in Italian or English
- Always confirm before taking action
- Use the provided functions for all operations
- Never ask for phone number - it's {caller_phone}"""

def get_tools_config():
    """Return the tools configuration for OpenAI"""
    return [
        {
            "type": "function",
            "name": "check_slot_availability",
            "description": "Check if a specific spa time slot has available space for booking",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date to check in YYYY-MM-DD format (e.g., 2024-01-25)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time to check in HH:MM format (e.g., 10:00, 14:00)"
                    }
                },
                "required": ["date", "start_time"]
            }
        },
        {
            "type": "function",
            "name": "book_spa_slot",
            "description": "Book a confirmed spa session for a customer after checking availability",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Customer's full name"
                    },
                    "date": {
                        "type": "string",
                        "description": "Booking date in YYYY-MM-DD format"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Session start time in HH:MM format (e.g., 10:00)"
                    }
                },
                "required": ["name", "date", "start_time"]
            }
        },
        {
            "type": "function",
            "name": "get_latest_appointment",
            "description": "Retrieve the most recent or upcoming appointment for the calling customer",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "type": "function",
            "name": "delete_appointment",
            "description": "Cancel/delete an existing appointment after confirming with customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_reference": {
                        "type": "string",
                        "description": "Booking reference code (e.g., SPA-000123) from get_latest_appointment"
                    }
                },
                "required": []
            }
        }
    ]

# ============================================
#              API ENDPOINTS
# ============================================

@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        result = supabase.table('spa_bookings').select('count', count='exact').limit(1).execute()
        db_status = "connected"
        
        # Get conversation stats
        conv_stats = supabase.table('conversations').select('count', count='exact').execute()
        conversation_count = conv_stats.count if hasattr(conv_stats, 'count') else 0
        
    except Exception as e:
        db_status = f"error: {str(e)}"
        conversation_count = 0
    
    return {
        "status": "healthy",
        "service": "Spa Booking System",
        "version": "2.0.0",
        "features": ["conversation_logging", "tool_calling", "transcription"],
        "model": OPENAI_MODEL,
        "spa_name": Config.SPA_NAME,
        "database": db_status,
        "total_conversations_logged": conversation_count
    }

@app.post("/webhook/incoming-call")
async def handle_incoming_call(
    From: str = Form(...),
    CallSid: str = Form(...),
    To: str = Form(...)
):
    """Twilio webhook - receives call information and returns TwiML"""
    logger.info(f"📞 Incoming call from {From} (CallSid: {CallSid})")
    
    try:
        # Store call session
        call_session = supabase.table('call_sessions').insert({
            'phone_number': From,
            'call_id': CallSid,
            'status': 'initiated',
            'country': 'IT'
        }).execute()
        logger.info(f"📝 Call session stored: {call_session.data[0]['id']}")
    except Exception as e:
        logger.error(f"Failed to store call session: {e}")
    
    # Create TwiML response
    response = VoiceResponse()
    connect = Connect()
    
    # Create Stream with WebSocket URL
    stream_url = f'wss://{RENDER_EXTERNAL_HOSTNAME}/media-stream'
    stream = Stream(url=stream_url)
    
    # Pass custom parameters
    stream.parameter(name='customerPhone', value=From)
    stream.parameter(name='callSid', value=CallSid)
    stream.parameter(name='twilioNumber', value=To)
    
    connect.append(stream)
    response.append(connect)
    
    # Initial greeting
    response.say('Benvenuto, la sto mettendo in contatto con Sara.', voice='alice', language='it-IT')
    
    return Response(content=str(response), media_type='application/xml')

@app.websocket("/media-stream")
async def media_stream_handler(websocket: WebSocket):
    """Handle Twilio Media Streams WebSocket connection with full logging"""
    logger.info("🔌 WebSocket connection attempt")
    
    try:
        await websocket.accept()
        logger.info("✅ WebSocket accepted")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket: {e}")
        return
    
    openai_ws = None
    conversation_log = None
    
    try:
        # Connect to OpenAI Realtime API
        openai_url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
        
        async with websockets.connect(
            openai_url,
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            logger.info("✅ Connected to OpenAI Realtime API")
            
            # Shared state
            stream_sid = None
            customer_phone = None
            call_sid = None
            session_initialized = False
            
            # Transcript buffers for streaming
            current_ai_transcript = ""
            
            async def receive_from_twilio():
                """Receive audio from Twilio and forward to OpenAI"""
                nonlocal stream_sid, customer_phone, call_sid, session_initialized
                nonlocal conversation_log
                
                try:
                    async for message in websocket.iter_text():
                        try:
                            data = json.loads(message)
                            event_type = data.get('event')
                            
                            if event_type == 'connected':
                                logger.info(f"📨 Connected event received")
                            
                            elif event_type == 'start':
                                # Extract metadata
                                stream_sid = data['start'].get('streamSid')
                                custom_params = data['start'].get('customParameters', {})
                                customer_phone = custom_params.get('customerPhone', 'Unknown')
                                call_sid = custom_params.get('callSid', 'Unknown')
                                
                                logger.info(f"📞 Stream started - Phone: {customer_phone}")
                                
                                # Create conversation log
                                conversation_log = ConversationLog(
                                    conversation_id=stream_sid,
                                    customer_phone=customer_phone,
                                    call_sid=call_sid,
                                    stream_sid=stream_sid,
                                    started_at=datetime.now().isoformat(),
                                    metadata={
                                        'twilio_number': custom_params.get('twilioNumber'),
                                        'model': OPENAI_MODEL
                                    }
                                )
                                conversation_logger.create_conversation(conversation_log)
                                
                                # Update call session
                                try:
                                    supabase.table('call_sessions').update({
                                        'status': 'connected'
                                    }).eq('call_id', call_sid).execute()
                                except:
                                    pass
                                
                                # Initialize OpenAI session with transcription enabled
                                session_config = {
                                    "type": "session.update",
                                    "session": {
                                        "modalities": ["audio", "text"],
                                        "voice": VOICE,
                                        "input_audio_format": "g711_ulaw",
                                        "output_audio_format": "g711_ulaw",
                                        "input_audio_transcription": {
                                            "model": "whisper-1"
                                        },
                                        "turn_detection": {
                                            "type": "server_vad",
                                            "threshold": 0.5,
                                            "prefix_padding_ms": 300,
                                            "silence_duration_ms": 500
                                        },
                                        "instructions": get_system_message(customer_phone),
                                        "temperature": 0.8,
                                        "tools": get_tools_config(),
                                        "tool_choice": "auto"
                                    }
                                }
                                
                                await openai_ws.send(json.dumps(session_config))
                                session_initialized = True
                                logger.info("🔧 Session configured with transcription & tools")
                            
                            elif event_type == 'media' and stream_sid and session_initialized:
                                # Forward audio to OpenAI
                                audio_payload = data['media']['payload']
                                audio_append = {
                                    "type": "input_audio_buffer.append",
                                    "audio": audio_payload
                                }
                                await openai_ws.send(json.dumps(audio_append))
                            
                            elif event_type == 'stop':
                                logger.info("📞 Call ended")
                                if stream_sid:
                                    conversation_logger.end_conversation(stream_sid)
                                
                                # Update call session
                                try:
                                    supabase.table('call_sessions').update({
                                        'status': 'completed',
                                        'ended_at': datetime.now().isoformat()
                                    }).eq('call_id', call_sid).execute()
                                except:
                                    pass
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON from Twilio: {e}")
                            continue
                            
                except WebSocketDisconnect:
                    logger.info("Twilio WebSocket disconnected")
                    if stream_sid:
                        conversation_logger.end_conversation(stream_sid)
                except Exception as e:
                    logger.error(f"Error in receive_from_twilio: {e}", exc_info=True)
            
            async def send_to_twilio():
                """Receive from OpenAI and forward to Twilio"""
                nonlocal stream_sid, customer_phone, current_ai_transcript
                
                try:
                    async for message in openai_ws:
                        try:
                            response = json.loads(message)
                            response_type = response.get('type')
                            
                            # ===== USER TRANSCRIPT (What customer said) =====
                            if response_type == 'conversation.item.input_audio_transcription.completed':
                                transcript = response.get('transcript', '')
                                if transcript and stream_sid:
                                    logger.info(f"🎤 Customer: {transcript}")
                                    
                                    turn = ConversationTurn(
                                        timestamp=datetime.now().isoformat(),
                                        role="user",
                                        transcript=transcript,
                                        event_id=response.get('event_id'),
                                        item_id=response.get('item_id')
                                    )
                                    conversation_logger.add_turn(stream_sid, turn)
                            
                            # ===== AI TRANSCRIPT STREAMING =====
                            elif response_type == 'response.audio_transcript.delta':
                                delta = response.get('delta', '')
                                current_ai_transcript += delta
                            
                            # ===== AI TRANSCRIPT COMPLETE =====
                            elif response_type == 'response.audio_transcript.done':
                                transcript = response.get('transcript', '')
                                if transcript and stream_sid:
                                    logger.info(f"🤖 Assistant: {transcript}")
                                    
                                    turn = ConversationTurn(
                                        timestamp=datetime.now().isoformat(),
                                        role="assistant",
                                        transcript=transcript,
                                        event_id=response.get('event_id'),
                                        item_id=response.get('item_id')
                                    )
                                    conversation_logger.add_turn(stream_sid, turn)
                                
                                current_ai_transcript = ""
                            
                            # ===== AUDIO OUTPUT TO TWILIO =====
                            elif response_type == 'response.audio.delta' and stream_sid:
                                audio_delta = response.get('delta')
                                if audio_delta:
                                    twilio_message = {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {
                                            "payload": audio_delta
                                        }
                                    }
                                    await websocket.send_json(twilio_message)
                            
                            # ===== FUNCTION CALL HANDLING =====
                            elif response_type == 'response.function_call_arguments.done':
                                function_name = response.get('name')
                                call_id = response.get('call_id')
                                arguments = json.loads(response.get('arguments', '{}'))
                                
                                logger.info(f"🔧 Function call: {function_name}({arguments})")
                                
                                # Log function call start
                                function_call = FunctionCall(
                                    timestamp=datetime.now().isoformat(),
                                    function_name=function_name,
                                    arguments=arguments,
                                    call_id=call_id
                                )
                                
                                # Execute function
                                start_time = time.time()
                                result = await execute_function(function_name, arguments, customer_phone)
                                execution_time = int((time.time() - start_time) * 1000)
                                
                                # Update function call with result
                                function_call.result = result
                                function_call.success = not result.get('error')
                                function_call.error_message = result.get('error')
                                function_call.execution_time_ms = execution_time
                                
                                # Log to database
                                if stream_sid:
                                    conversation_logger.add_function_call(stream_sid, function_call)
                                
                                # Send result back to OpenAI
                                function_output = {
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": call_id,
                                        "output": json.dumps(result)
                                    }
                                }
                                await openai_ws.send(json.dumps(function_output))
                                
                                # Trigger response generation
                                await openai_ws.send(json.dumps({"type": "response.create"}))
                            
                            # Log other important events
                            elif response_type and 'error' in response_type.lower():
                                logger.error(f"❌ OpenAI error: {response}")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON from OpenAI: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error in send_to_twilio: {e}", exc_info=True)
            
            # Run both tasks concurrently
            await asyncio.gather(
                receive_from_twilio(),
                send_to_twilio()
            )
            
    except Exception as e:
        logger.error(f"Fatal error in media_stream_handler: {e}", exc_info=True)
    finally:
        logger.info("WebSocket handler completed")
        try:
            await websocket.close()
        except:
            pass

async def execute_function(function_name: str, arguments: dict, customer_phone: str) -> dict:
    """Execute the requested function using Supabase RPC calls"""
    
    logger.info(f"📋 Executing: {function_name}")
    
    try:
        if function_name == "check_slot_availability":
            start_time = format_time_for_db(arguments.get('start_time'))
            date = arguments.get('date')
            
            result = supabase.rpc('check_slot_availability', {
                'p_date': date,
                'p_start_time': start_time
            }).execute()
            
            if result.data:
                data = result.data
                if data.get('status') == 'success':
                    return {
                        "available": True,
                        "spots_remaining": data.get('spots_remaining', 0),
                        "message": f"Slot available with {data.get('spots_remaining')} spots"
                    }
                else:
                    return {
                        "available": False,
                        "message": data.get('message', 'Slot full')
                    }
            
            return {"available": False, "message": "Error checking availability"}
        
        elif function_name == "book_spa_slot":
            start_time = format_time_for_db(arguments.get('start_time'))
            end_time = calculate_end_time(arguments.get('start_time'))
            
            result = supabase.rpc('book_spa_slot', {
                'p_customer_name': arguments.get('name'),
                'p_customer_phone': customer_phone,
                'p_booking_date': arguments.get('date'),
                'p_slot_start_time': start_time,
                'p_slot_end_time': end_time
            }).execute()
            
            if result.data:
                data = result.data
                if data.get('status') == 'success':
                    # Link booking to call session
                    try:
                        booking_id = data.get('booking_id')
                        if booking_id:
                            supabase.table('call_sessions').update({
                                'booking_id': booking_id
                            }).eq('phone_number', customer_phone).eq('status', 'connected').execute()
                    except:
                        pass
                    
                    return {
                        "success": True,
                        "booking_reference": data.get('booking_reference'),
                        "message": f"Booking confirmed. Reference: {data.get('booking_reference')}"
                    }
                else:
                    return {
                        "success": False,
                        "message": data.get('message', 'Booking failed')
                    }
            
            return {"success": False, "message": "Booking error"}
        
        elif function_name == "get_latest_appointment":
            result = supabase.rpc('get_latest_appointment', {
                'p_phone_number': customer_phone
            }).execute()
            
            if result.data:
                data = result.data
                if data.get('status') == 'success':
                    booking = data.get('booking', {})
                    return {
                        "found": True,
                        "booking_reference": booking.get('reference'),
                        "customer_name": booking.get('customer_name'),
                        "date": booking.get('date_formatted'),
                        "time": booking.get('time_slot'),
                        "message": f"Found booking: {booking.get('reference')} for {booking.get('date_formatted')} at {booking.get('time_slot')}"
                    }
                else:
                    return {
                        "found": False,
                        "message": "No bookings found"
                    }
            
            return {"found": False, "message": "No bookings found"}
        
        elif function_name == "delete_appointment":
            booking_reference = arguments.get('booking_reference')
            
            if not booking_reference:
                # Get latest appointment first
                latest_result = supabase.rpc('get_latest_appointment', {
                    'p_phone_number': customer_phone
                }).execute()
                
                if latest_result.data and latest_result.data.get('status') == 'success':
                    booking = latest_result.data.get('booking', {})
                    booking_reference = booking.get('reference')
                else:
                    return {
                        "success": False,
                        "message": "No booking found to cancel"
                    }
            
            result = supabase.rpc('delete_appointment', {
                'p_phone_number': customer_phone,
                'p_booking_reference': booking_reference
            }).execute()
            
            if result.data:
                data = result.data
                if data.get('status') == 'success':
                    return {
                        "success": True,
                        "message": data.get('message', 'Booking cancelled')
                    }
                else:
                    return {
                        "success": False,
                        "message": data.get('message', 'Cancellation failed')
                    }
            
            return {"success": False, "message": "Cancellation error"}
        
        else:
            return {"error": f"Unknown function: {function_name}"}
            
    except Exception as e:
        logger.error(f"Error executing {function_name}: {e}", exc_info=True)
        return {"error": f"System error: {str(e)}"}

# ============================================
#     CONVERSATION EXPORT & ANALYTICS
# ============================================

@app.get("/api/conversations/{conversation_id}/transcript")
async def get_transcript(conversation_id: str):
    """Get formatted transcript for a conversation"""
    try:
        # Get conversation from database
        conv_result = supabase.table('conversations').select('*').eq('conversation_id', conversation_id).execute()
        
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv = conv_result.data[0]
        
        # Get transcript using RPC function
        transcript_result = supabase.rpc('get_conversation_transcript', {
            'p_conversation_id': conv['id']
        }).execute()
        
        return {
            "conversation_id": conversation_id,
            "customer_phone": conv['customer_phone'],
            "started_at": conv['started_at'],
            "ended_at": conv['ended_at'],
            "duration_seconds": conv['duration_seconds'],
            "transcript": transcript_result.data
        }
        
    except Exception as e:
        logger.error(f"Error getting transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str):
    """Export complete conversation data (ElevenLabs-style)"""
    try:
        # Get conversation
        conv_result = supabase.table('conversations').select('*').eq('conversation_id', conversation_id).execute()
        
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv = conv_result.data[0]
        db_id = conv['id']
        
        # Get all turns
        turns_result = supabase.table('conversation_turns').select('*').eq('conversation_id', db_id).order('timestamp').execute()
        
        # Get all function calls
        functions_result = supabase.table('function_calls').select('*').eq('conversation_id', db_id).order('timestamp').execute()
        
        # Get associated booking if any
        booking_result = supabase.table('spa_bookings').select('*').eq('customer_phone', conv['customer_phone']).execute()
        
        return {
            "conversation": {
                "id": conversation_id,
                "customer_phone": conv['customer_phone'],
                "call_sid": conv['call_sid'],
                "started_at": conv['started_at'],
                "ended_at": conv['ended_at'],
                "duration_seconds": conv['duration_seconds'],
                "model_used": conv['model_used'],
                "total_turns": conv['total_turns'],
                "total_functions_called": conv['total_functions_called']
            },
            "turns": [
                {
                    "turn_number": turn['turn_number'],
                    "timestamp": turn['timestamp'],
                    "role": turn['role'],
                    "transcript": turn['transcript'],
                    "audio_duration_ms": turn['audio_duration_ms']
                }
                for turn in turns_result.data
            ],
            "function_calls": [
                {
                    "timestamp": func['timestamp'],
                    "function_name": func['function_name'],
                    "arguments": func['arguments'],
                    "result": func['result'],
                    "success": func['success'],
                    "execution_time_ms": func['execution_time_ms']
                }
                for func in functions_result.data
            ],
            "bookings": [
                {
                    "reference": booking['booking_reference'],
                    "date": booking['booking_date'],
                    "time": f"{booking['slot_start_time']} - {booking['slot_end_time']}",
                    "status": booking['status']
                }
                for booking in booking_result.data
                if booking['created_at'] >= conv['started_at'] and 
                   booking['created_at'] <= (conv['ended_at'] or datetime.now().isoformat())
            ]
        }
        
    except Exception as e:
        logger.error(f"Error exporting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/recent")
async def get_recent_conversations(limit: int = 10):
    """Get recent conversations with summary"""
    try:
        result = supabase.table('conversation_summaries').select('*').order('started_at', desc=True).limit(limit).execute()
        
        return {
            "conversations": result.data,
            "count": len(result.data)
        }
        
    except Exception as e:
        logger.error(f"Error getting recent conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/function-handler")
async def function_handler(request: Request):
    """REST endpoint for testing function calls"""
    try:
        data = await request.json()
        function_name = data.get("function_name")
        arguments = data.get("arguments", {})
        customer_phone = data.get("customer_phone", "+39 333 123 4567")
        
        result = await execute_function(function_name, arguments, customer_phone)
        return result
        
    except Exception as e:
        logger.error(f"Error in REST function handler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🚀 Starting Spa Booking System v2.0")
    logger.info(f"📍 Spa Name: {Config.SPA_NAME}")
    logger.info(f"🎙️ Voice: {VOICE}")
    logger.info(f"🤖 Model: {OPENAI_MODEL}")
    logger.info(f"🗄️ Supabase: {Config.SUPABASE_URL}")
    logger.info(f"📝 Conversation Logging: ENABLED")
    logger.info(f"🔧 Tool Calling: ENABLED")
    uvicorn.run(app, host="0.0.0.0", port=port)