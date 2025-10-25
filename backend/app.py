"""
Spa Booking System - FastAPI implementation with Supabase integration
Handles Twilio Media Streams, OpenAI Realtime API, and Supabase database
"""

import asyncio
import base64
import json
import os
import time
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Form
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import websockets
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Spa Booking System", version="1.0.0")

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
    logger.error("❌ OPENAI_API_KEY not found in environment variables!")
    raise ValueError("OPENAI_API_KEY is required")

if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
    logger.error("❌ SUPABASE_URL and SUPABASE_KEY are required!")
    raise ValueError("Supabase configuration is required")

# Initialize Supabase client
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
logger.info(f"✅ Connected to Supabase at {Config.SUPABASE_URL}")

def format_time_for_db(time_str: str) -> str:
    """Convert HH:MM to HH:MM:SS for database TIME field"""
    if time_str and len(time_str) == 5:  # HH:MM format
        return f"{time_str}:00"
    return time_str

def calculate_end_time(start_time: str) -> str:
    """Calculate end time based on 2-hour session duration"""
    try:
        # Parse start time
        hour, minute = map(int, start_time.split(':')[:2])
        
        # Add 2 hours
        end_hour = hour + Config.SESSION_DURATION_HOURS
        
        # Format as HH:MM:SS
        return f"{end_hour:02d}:{minute:02d}:00"
    except:
        # Default fallback
        return "12:00:00"

def get_system_message(caller_phone):
    """Generate system message with actual values, not templates"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return f"""# Role
You are Sara, a warm and professional AI receptionist for {Config.SPA_NAME}, a luxury wellness spa in Italy. You handle phone bookings with grace, patience, and efficiency.

# Context
- Current date/time: {current_time}
- Caller's phone: {caller_phone} (automatically provided - NEVER ask for it)
- Operating hours: Monday-Saturday 10:00-20:00, Sunday CLOSED
- Session duration: {Config.SESSION_DURATION_HOURS} hours per slot
- Maximum capacity: {Config.MAX_CAPACITY_PER_SLOT} people per time slot
- Available slots: 10:00-12:00, 12:00-14:00, 14:00-16:00, 16:00-18:00, 18:00-20:00

# Primary Objectives
1. Determine intent: Book NEW, CHECK existing, CANCEL, or RESCHEDULE appointment
2. Handle requests efficiently while maintaining a warm, conversational tone
3. Confirm all details before taking action
4. Never leave the caller confused or waiting in silence

# Conversation Flows

## 1. NEW BOOKING Flow
**Step 1 - Greeting & Intent**
- Italian: "Buongiorno! Grazie per aver chiamato {Config.SPA_NAME}. Sono Sara. Come posso aiutarla oggi?"
- English: "Good morning! Thank you for calling {Config.SPA_NAME}. This is Sara. How may I assist you today?"
- Listen for language preference and continue in that language

**Step 2 - Gather Information** (One question at a time)
- Name: "Posso avere il suo nome, per favore?" / "May I have your name, please?"
- Date: "Per quale giorno vorrebbe prenotare?" / "Which day would you like to book?"
- Time preference: "A che ora preferirebbe?" / "What time would you prefer?"

**Step 3 - Check Availability**
- Say: "Un momento, controllo la disponibilità..." / "One moment, let me check availability..."
- Call: check_slot_availability(date, start_time)
- Analyze response and offer alternatives if needed

**Step 4 - Confirm Booking**
- Summarize: "Perfetto! Conferma prenotazione per [name] il [date] alle [time]?" 
- Upon confirmation, call: book_spa_slot(name, date, start_time, end_time)
- Confirm: "Ottimo! La sua prenotazione è confermata. Il codice è [reference]. La aspettiamo!"

## 2. CHECK APPOINTMENT Flow
**Immediate Action**
- Call: get_latest_appointment with phone number {caller_phone}
- If found: "Ho trovato la sua prenotazione per il [date] alle [time]. Desidera altro?"
- If not found: "Non trovo prenotazioni con questo numero. Vuole prenotarne una nuova?"

## 3. CANCELLATION Flow
**Step 1 - Find Appointment**
- Call: get_latest_appointment with phone number {caller_phone}
- Read details: "Ho trovato la prenotazione del [date] alle [time]. È questa che vuole cancellare?"

**Step 2 - Confirm & Cancel**
- ONLY upon explicit confirmation ("sì"/"yes"), call: delete_appointment(phone_number, booking_reference)
- Confirm: "La prenotazione è stata cancellata. Vuole prenotare un altro appuntamento?"

# Critical Guidelines

## Language & Tone
- Detect language from first response and stick to it
- Speak naturally, not robotically (say "alle cinque" not "alle diciassette e zero zero")
- Be warm but professional - you're Sara, not a machine
- Keep responses concise but friendly

## Data Handling
- Phone number is {caller_phone} - NEVER ask for it
- Always confirm details before any action
- Format dates clearly: "venerdì 15 gennaio" not just "15/01"
- Use 24-hour time internally but speak naturally

## Error Prevention
- Book ONLY during operating hours (Mon-Sat 10:00-20:00)
- Check availability before confirming
- Never double-book the same slot beyond capacity
- Validate dates (no past bookings)

# Remember
- You are Sara, not a robot
- Every call is important
- Patience and warmth win customers
- Confirm before acting
- The phone number is already known: {caller_phone}"""

def get_tools_config():
    """Return the tools configuration for OpenAI"""
    return [
        {
            "type": "function",
            "name": "check_slot_availability",
            "description": "Check if a spa time slot has available space",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM format (e.g., 10:00, 14:00)"
                    }
                },
                "required": ["date", "start_time"]
            }
        },
        {
            "type": "function",
            "name": "book_spa_slot",
            "description": "Book a spa session for a customer",
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
                        "description": "Session start time in HH:MM format"
                    }
                },
                "required": ["name", "date", "start_time"]
            }
        },
        {
            "type": "function",
            "name": "get_latest_appointment",
            "description": "Retrieve the most recent appointment for a customer by phone number",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "type": "function",
            "name": "delete_appointment",
            "description": "Cancel/delete a customer's appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_reference": {
                        "type": "string",
                        "description": "Booking reference code (e.g., SPA-000123)"
                    }
                },
                "required": []
            }
        }
    ]

@app.get("/")
async def health_check():
    """Health check endpoint"""
    # Test Supabase connection
    try:
        result = supabase.table('spa_bookings').select('count', count='exact').limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "Spa Booking System",
        "version": "1.0.0",
        "model": OPENAI_MODEL,
        "spa_name": Config.SPA_NAME,
        "database": db_status
    }

@app.post("/webhook/incoming-call")
async def handle_incoming_call(
    From: str = Form(...),
    CallSid: str = Form(...),
    To: str = Form(...)
):
    """
    Twilio webhook - receives call information and returns TwiML
    """
    logger.info(f"📞 Incoming call from {From} (CallSid: {CallSid})")
    
    try:
        # Store call session in database
        call_session = supabase.table('call_sessions').insert({
            'phone_number': From,
            'call_id': CallSid,
            'status': 'initiated',
            'country': 'IT'
        }).execute()
        logger.info(f"📝 Call session stored: {call_session.data[0]['id']}")
    except Exception as e:
        logger.error(f"❌ Failed to store call session: {e}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Create Connect verb
    connect = Connect()
    
    # Create Stream verb with WebSocket URL
    stream_url = f'wss://{RENDER_EXTERNAL_HOSTNAME}/media-stream'
    stream = Stream(url=stream_url)
    
    # Add custom parameters that will be passed to the WebSocket
    stream.parameter(name='customerPhone', value=From)
    stream.parameter(name='callSid', value=CallSid)
    stream.parameter(name='twilioNumber', value=To)
    
    # Append stream to connect
    connect.append(stream)
    
    # Append connect to response
    response.append(connect)
    
    # Add initial greeting while connecting
    response.say('Benvenuto, la sto mettendo in contatto con il nostro assistente.', voice='alice', language='it-IT')
    
    twiml = str(response)
    logger.info(f"📤 Returning TwiML response (length: {len(twiml)} chars)")
    
    return Response(content=twiml, media_type='application/xml')

@app.websocket("/media-stream")
async def media_stream_handler(websocket: WebSocket):
    """Handle Twilio Media Streams WebSocket connection"""
    logger.info("🔌 WebSocket connection attempt")
    
    try:
        await websocket.accept()
        logger.info("✅ WebSocket accepted")
    except Exception as e:
        logger.error(f"❌ Failed to accept WebSocket: {e}")
        return
    
    openai_ws = None
    
    try:
        # Connect to OpenAI Realtime API FIRST (before processing Twilio events)
        openai_url = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
        
        logger.info(f"🔌 Connecting to OpenAI at: {openai_url}")
        
        async with websockets.connect(
            openai_url,
            additional_headers={  # ✅ Correct parameter name (not extra_headers)
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
            
            async def receive_from_twilio():
                """Receive audio from Twilio and forward to OpenAI"""
                nonlocal stream_sid, customer_phone, call_sid, session_initialized
                
                try:
                    async for message in websocket.iter_text():
                        try:
                            data = json.loads(message)
                            event_type = data.get('event')
                            
                            if event_type == 'connected':
                                logger.info(f"📨 Event: connected")
                                logger.info(f"   Protocol: {data.get('protocol')}, Version: {data.get('version')}")
                            
                            elif event_type == 'start':
                                # Extract stream metadata
                                stream_sid = data['start'].get('streamSid')
                                
                                # Extract custom parameters
                                custom_params = data['start'].get('customParameters', {})
                                customer_phone = custom_params.get('customerPhone', 'Unknown')
                                call_sid = custom_params.get('callSid', 'Unknown')
                                
                                logger.info(f"📨 Event: start")
                                logger.info(f"   StreamSid: {stream_sid}")
                                logger.info(f"   Customer: {customer_phone}")
                                logger.info(f"   CallSid: {call_sid}")
                                
                                # Update call session status
                                try:
                                    supabase.table('call_sessions').update({
                                        'status': 'connected'
                                    }).eq('call_id', call_sid).execute()
                                except Exception as e:
                                    logger.error(f"Failed to update call session: {e}")
                                
                                # Initialize OpenAI session with customer info
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
                                logger.info("🔧 OpenAI session configured with tools")
                            
                            elif event_type == 'media' and stream_sid and session_initialized:
                                # Forward audio to OpenAI
                                audio_payload = data['media']['payload']
                                audio_append = {
                                    "type": "input_audio_buffer.append",
                                    "audio": audio_payload
                                }
                                await openai_ws.send(json.dumps(audio_append))
                            
                            elif event_type == 'stop':
                                logger.info("📨 Event: stop - Call ended")
                                # Update call session status
                                try:
                                    supabase.table('call_sessions').update({
                                        'status': 'completed',
                                        'ended_at': datetime.now().isoformat()
                                    }).eq('call_id', call_sid).execute()
                                except Exception as e:
                                    logger.error(f"Failed to update call session: {e}")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Invalid JSON from Twilio: {e}")
                            continue
                            
                except WebSocketDisconnect:
                    logger.info("📞 Twilio WebSocket disconnected")
                except Exception as e:
                    logger.error(f"❌ Error in receive_from_twilio: {e}", exc_info=True)
            
            async def send_to_twilio():
                """Receive from OpenAI and forward to Twilio"""
                nonlocal stream_sid, customer_phone
                
                try:
                    async for message in openai_ws:
                        try:
                            response = json.loads(message)
                            response_type = response.get('type')
                            
                            # Handle audio output
                            if response_type == 'response.audio.delta' and stream_sid:
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
                            
                            # Log transcriptions
                            elif response_type == 'conversation.item.input_audio_transcription.completed':
                                transcript = response.get('transcript', '')
                                if transcript:
                                    logger.info(f"🎤 Customer said: {transcript}")
                            
                            # Handle function calls
                            elif response_type == 'response.function_call_arguments.done':
                                function_name = response.get('name')
                                call_id = response.get('call_id')
                                arguments = json.loads(response.get('arguments', '{}'))
                                
                                logger.info(f"🔧 Function call: {function_name}({arguments})")
                                
                                # Execute function and get result
                                result = await execute_function(function_name, arguments, customer_phone)
                                
                                # Send function result back to OpenAI
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
                            
                            # Log other events for debugging
                            elif response_type and 'error' in response_type.lower():
                                logger.error(f"❌ OpenAI error: {response}")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Invalid JSON from OpenAI: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"❌ Error in send_to_twilio: {e}", exc_info=True)
            
            # Run both tasks concurrently
            await asyncio.gather(
                receive_from_twilio(),
                send_to_twilio()
            )
            
    except Exception as e:
        logger.error(f"❌ Fatal error in media_stream_handler: {e}", exc_info=True)
    finally:
        logger.info("🔌 WebSocket handler completed")
        try:
            await websocket.close()
        except:
            pass

async def execute_function(function_name: str, arguments: dict, customer_phone: str) -> dict:
    """Execute the requested function using Supabase RPC calls"""
    
    logger.info(f"📋 Executing function: {function_name} with args: {arguments}")
    
    try:
        if function_name == "check_slot_availability":
            # Format time for database (add :00 for seconds)
            start_time = format_time_for_db(arguments.get('start_time'))
            date = arguments.get('date')
            
            # Call Supabase RPC function
            result = supabase.rpc('check_slot_availability', {
                'p_date': date,
                'p_start_time': start_time
            }).execute()
            
            logger.info(f"✅ Availability check result: {result.data}")
            
            # Parse the response
            if result.data:
                data = result.data
                if data.get('status') == 'success':
                    return {
                        "available": data.get('available', False),
                        "spots_remaining": data.get('spots_remaining', 0),
                        "message": f"Lo slot delle {arguments.get('start_time')} del {date} ha {data.get('spots_remaining')} posti disponibili su {data.get('total_capacity')}"
                    }
                else:
                    return {
                        "available": False,
                        "message": data.get('message', 'Slot non disponibile')
                    }
            
            return {
                "available": False,
                "message": "Errore nel controllo disponibilità"
            }
        
        elif function_name == "book_spa_slot":
            # Format times for database
            start_time = format_time_for_db(arguments.get('start_time'))
            # Calculate end time (2 hours later)
            end_time = calculate_end_time(arguments.get('start_time'))
            
            # Call Supabase RPC function
            result = supabase.rpc('book_spa_slot', {
                'p_customer_name': arguments.get('name'),
                'p_customer_phone': customer_phone,
                'p_booking_date': arguments.get('date'),
                'p_slot_start_time': start_time,
                'p_slot_end_time': end_time
            }).execute()
            
            logger.info(f"✅ Booking result: {result.data}")
            
            # Parse the response
            if result.data:
                data = result.data
                if data.get('status') == 'success':
                    # Update call session with booking ID
                    try:
                        booking_id = data.get('booking_id')
                        if booking_id:
                            supabase.table('call_sessions').update({
                                'booking_id': booking_id
                            }).eq('phone_number', customer_phone).eq('status', 'connected').execute()
                    except Exception as e:
                        logger.error(f"Failed to link booking to call session: {e}")
                    
                    return {
                        "success": True,
                        "booking_reference": data.get('booking_reference'),
                        "message": f"Perfetto! La prenotazione è confermata. Il codice è {data.get('booking_reference')}. {data.get('message')}"
                    }
                else:
                    return {
                        "success": False,
                        "message": data.get('message', 'Non è stato possibile completare la prenotazione')
                    }
            
            return {
                "success": False,
                "message": "Errore durante la prenotazione"
            }
        
        elif function_name == "get_latest_appointment":
            # Call Supabase RPC function
            result = supabase.rpc('get_latest_appointment', {
                'p_phone_number': customer_phone
            }).execute()
            
            logger.info(f"✅ Latest appointment result: {result.data}")
            
            # Parse the response
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
                        "is_future": booking.get('is_future'),
                        "message": f"Ho trovato la sua prenotazione: {booking.get('customer_name')} per il {booking.get('date_formatted')} alle {booking.get('time_slot')}. Codice: {booking.get('reference')}"
                    }
                else:
                    return {
                        "found": False,
                        "message": data.get('message', 'Nessuna prenotazione trovata per questo numero')
                    }
            
            return {
                "found": False,
                "message": "Nessuna prenotazione trovata"
            }
        
        elif function_name == "delete_appointment":
            # First get the latest appointment if no reference provided
            booking_reference = arguments.get('booking_reference')
            
            if not booking_reference:
                # Get the latest appointment first
                latest_result = supabase.rpc('get_latest_appointment', {
                    'p_phone_number': customer_phone
                }).execute()
                
                if latest_result.data and latest_result.data.get('status') == 'success':
                    booking = latest_result.data.get('booking', {})
                    booking_reference = booking.get('reference')
                else:
                    return {
                        "success": False,
                        "message": "Nessuna prenotazione trovata da cancellare"
                    }
            
            # Now delete the appointment
            result = supabase.rpc('delete_appointment', {
                'p_phone_number': customer_phone,
                'p_booking_reference': booking_reference
            }).execute()
            
            logger.info(f"✅ Delete result: {result.data}")
            
            # Parse the response
            if result.data:
                data = result.data
                if data.get('status') == 'success':
                    return {
                        "success": True,
                        "message": data.get('message', 'Prenotazione cancellata con successo'),
                        "cancelled_booking": data.get('cancelled_booking')
                    }
                else:
                    return {
                        "success": False,
                        "message": data.get('message', 'Non è stato possibile cancellare la prenotazione')
                    }
            
            return {
                "success": False,
                "message": "Errore durante la cancellazione"
            }
        
        else:
            return {
                "error": f"Unknown function: {function_name}"
            }
            
    except Exception as e:
        logger.error(f"❌ Error executing function {function_name}: {e}", exc_info=True)
        return {
            "error": f"Errore del sistema: {str(e)}"
        }

@app.post("/api/function-handler")
async def function_handler(request: Request):
    """REST endpoint for function calls (if needed for testing)"""
    try:
        data = await request.json()
        function_name = data.get("function_name")
        arguments = data.get("arguments", {})
        customer_phone = data.get("customer_phone", "Unknown")
        
        result = await execute_function(function_name, arguments, customer_phone)
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in REST function handler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🚀 Starting Spa Booking System on port {port}")
    logger.info(f"📍 Spa Name: {Config.SPA_NAME}")
    logger.info(f"🎙️ Voice: {VOICE}")
    logger.info(f"🤖 Model: {OPENAI_MODEL}")
    logger.info(f"🗄️ Supabase: {Config.SUPABASE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=port)