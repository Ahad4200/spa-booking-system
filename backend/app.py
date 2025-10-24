"""
Spa Booking System - FastAPI implementation with proper async WebSocket handling
Handles Twilio Media Streams and OpenAI Realtime API integration
"""

import asyncio
import base64
import json
import os
import time
import logging
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import websockets
from dotenv import load_dotenv

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

# Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SPA_NAME = os.environ.get("SPA_NAME", "Santa Caterina Beauty Farm")
SESSION_DURATION_HOURS = int(os.environ.get("SESSION_DURATION_HOURS", "2"))
MAX_CAPACITY_PER_SLOT = int(os.environ.get("MAX_CAPACITY_PER_SLOT", "15"))

# System message for the AI
SYSTEM_MESSAGE = f"""# Role
You are Sara, a warm and professional AI receptionist for {SPA_NAME}, a luxury wellness spa in Italy. You handle phone bookings with grace, patience, and efficiency.

# Context
- Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')} Rome time (CEST/CET)
- Caller's phone: {{from}} (automatically provided by Twilio - NEVER ask for it)
- Operating hours: Monday-Saturday 10:00-20:00, Sunday CLOSED
- Session duration: {SESSION_DURATION_HOURS} hours per slot
- Maximum capacity: {MAX_CAPACITY_PER_SLOT} people per time slot
- Available slots: 10:00-12:00, 12:00-14:00, 14:00-16:00, 16:00-18:00, 18:00-20:00

# Primary Objectives
1. Determine intent: Book NEW, CHECK existing, CANCEL, or RESCHEDULE appointment
2. Handle requests efficiently while maintaining a warm, conversational tone
3. Confirm all details before taking action
4. Never leave the caller confused or waiting in silence

# Conversation Flows

## 1. NEW BOOKING Flow
**Step 1 - Greeting & Intent**
- Italian: "Buongiorno! Grazie per aver chiamato {SPA_NAME}. Sono Sara. Come posso aiutarla oggi?"
- English: "Good morning! Thank you for calling {SPA_NAME}. This is Sara. How may I assist you today?"
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
- Call: get_latest_appointment with caller's phone number
- If found: "Ho trovato la sua prenotazione per il [date] alle [time]. Desidera altro?"
- If not found: "Non trovo prenotazioni con questo numero. Vuole prenotarne una nuova?"

## 3. CANCELLATION Flow
**Step 1 - Find Appointment**
- Call: get_latest_appointment with caller's phone number
- Read details: "Ho trovato la prenotazione del [date] alle [time]. È questa che vuole cancellare?"

**Step 2 - Confirm & Cancel**
- ONLY upon explicit confirmation ("sì"/"yes"), call: delete_appointment(phone_number, booking_reference)
- Confirm: "La prenotazione è stata cancellata. Vuole prenotare un altro appuntamento?"

## 4. RESCHEDULE Flow
**Step 1 - Cancel Existing**
- Follow CANCELLATION flow to remove old appointment
- Store the customer_name for reuse

**Step 2 - Book New**
- Seamlessly transition: "Perfetto, quando vorrebbe venire invece?"
- Follow NEW BOOKING flow with stored name

# Critical Guidelines

## Language & Tone
- Detect language from first response and stick to it
- Speak naturally, not robotically (say "alle cinque" not "alle diciassette e zero zero")
- Be warm but professional - you're Sara, not a machine
- Keep responses concise but friendly

## Timing & Patience
- NEVER repeat yourself if the caller is silent - the system handles silence
- Allow natural pauses for thinking
- Don't rush the caller
- Wait for responses after success messages (they might have questions)

## Data Handling
- Phone number is AUTOMATICALLY provided ({{from}}) - NEVER ask for it
- Always confirm details before any action
- Format dates clearly: "venerdì 15 gennaio" not just "15/01"
- Use 24-hour time internally but speak naturally

## Error Prevention
- Book ONLY during operating hours (Mon-Sat 10:00-20:00)
- Check availability before confirming
- Never double-book the same slot beyond capacity
- Validate dates (no past bookings)

## Professional Boundaries
- Don't give medical or beauty advice
- Don't discuss prices (refer to website/reception)
- Don't share other customers' information
- Stay focused on booking management

# Tools Available

1. **check_slot_availability(date, start_time)**
   - Returns: available spots for the time slot
   - Use before confirming any booking

2. **book_spa_slot(name, date, start_time, end_time)**
   - Creates the appointment
   - Returns: booking reference code

3. **get_latest_appointment(phone_number)**
   - Finds customer's next/most recent appointment
   - Use phone: {{from}}

4. **delete_appointment(phone_number, booking_reference)**
   - Cancels an appointment
   - ONLY use after explicit confirmation

# Common Scenarios

**"What services do you offer?"**
"Offriamo sessioni spa di 2 ore con accesso completo alle nostre strutture wellness. Per informazioni dettagliate sui trattamenti specifici, può visitare il nostro sito web o chiedere alla reception."

**"How much does it cost?"**
"Per i prezzi aggiornati, la invito a consultare il nostro sito web o contattare la reception. Posso però aiutarla a prenotare il suo appuntamento."

**"Can I book for multiple people?"**
"Certo! Mi dica per quante persone e verifico la disponibilità. Ricordi che ogni slot può ospitare massimo {MAX_CAPACITY_PER_SLOT} persone."

**"I'm running late"**
"La ringrazio per averci avvisato. Il suo appuntamento è confermato. Se ha bisogno di cambiarlo, posso aiutarla."

# Emergency Responses

**If system is down:**
"Mi scusi, sto avendo difficoltà tecniche. Può richiamare tra qualche minuto o contattare la reception direttamente?"

**If slot is full:**
"Mi dispiace, quello slot è completo. Posso proporle [alternative times/dates]?"

**If caller is upset:**
"Capisco la sua frustrazione. Come posso aiutarla al meglio?"

# Remember
- You are Sara, not a robot
- Every call is important
- Patience and warmth win customers
- Confirm before acting
- The phone number is already known - focus on helping"""

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Spa Booking System",
        "version": "1.0.0"
    }

@app.post("/webhook/incoming-call")
async def handle_incoming_call(request: Request):
    """Twilio webhook - returns TwiML to connect to Media Stream"""
    logger.info("📞 Incoming call received")
    
    # Get the base URL for the WebSocket endpoint
    base_url = os.environ.get("BASE_URL", "https://spa-booking-system.onrender.com")
    websocket_url = f"{base_url}/media-stream"
    
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{websocket_url}" />
    </Connect>
</Response>'''
    
    logger.info(f"📞 Returning TwiML with WebSocket URL: {websocket_url}")
    return Response(content=twiml, media_type="application/xml")

@app.websocket("/media-stream")
async def media_stream_handler(twilio_ws: WebSocket):
    """Handle bidirectional audio streaming between Twilio and OpenAI"""
    logger.info("📞 Twilio WebSocket connected")
    await twilio_ws.accept()
    
    stream_sid = None
    call_start_time = None
    
    try:
        # Connect to OpenAI Realtime API
        openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        logger.info("🔌 Connecting to OpenAI Realtime API...")
        async with websockets.connect(openai_url, extra_headers=headers) as openai_ws:
            logger.info("✅ Connected to OpenAI Realtime API")
            
            # Send session configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": SYSTEM_MESSAGE,
                    "voice": "alloy",
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
                    "temperature": 0.7
                }
            }
            await openai_ws.send(json.dumps(session_config))
            logger.info("✅ Session configured")
            
            # Task: Forward audio from Twilio to OpenAI
            async def forward_twilio_to_openai():
                """Receive audio from Twilio, send to OpenAI"""
                nonlocal stream_sid, call_start_time
                try:
                    async for message in twilio_ws.iter_text():
                        data = json.loads(message)
                        
                        if data['event'] == 'start':
                            stream_sid = data['start']['streamSid']
                            call_start_time = time.time()
                            logger.info(f"📞 Stream started: {stream_sid}")
                            logger.info(f"📞 From: {data['start'].get('customParameters', {}).get('from', 'N/A')}")
                            
                        elif data['event'] == 'media':
                            # Forward audio to OpenAI
                            audio_payload = data['media']['payload']
                            logger.debug(f"🔊 Received {len(audio_payload)} bytes from Twilio")
                            
                            audio_append = {
                                "type": "input_audio_buffer.append",
                                "audio": audio_payload
                            }
                            await openai_ws.send(json.dumps(audio_append))
                            logger.debug(f"🔊 Forwarded {len(audio_payload)} bytes to OpenAI")
                            
                        elif data['event'] == 'stop':
                            call_duration = time.time() - call_start_time if call_start_time else 0
                            logger.info(f"📞 Call ended - Duration: {call_duration:.2f} seconds")
                            break
                            
                except WebSocketDisconnect:
                    logger.info("❌ Twilio disconnected")
                except Exception as e:
                    logger.error(f"❌ Error in Twilio handler: {e}")
            
            # Task: Forward audio from OpenAI to Twilio
            async def forward_openai_to_twilio():
                """Receive responses from OpenAI, send to Twilio"""
                try:
                    async for message in openai_ws:
                        response = json.loads(message)
                        
                        if response['type'] == 'session.updated':
                            logger.info("✅ OpenAI session updated")
                            
                        elif response['type'] == 'response.audio.delta':
                            # Forward audio response to Twilio
                            if response.get('delta') and stream_sid:
                                logger.debug(f"🎤 Sending {len(response['delta'])} bytes to Twilio")
                                
                                audio_message = {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": response['delta']
                                    }
                                }
                                await twilio_ws.send_json(audio_message)
                                
                        elif response['type'] == 'input_audio_buffer.speech_started':
                            logger.info("🎤 User started speaking")
                            
                        elif response['type'] == 'response.audio_transcript.delta':
                            transcript = response.get('delta', '')
                            if transcript:
                                logger.info(f"🤖 AI: {transcript}")
                                
                        elif response['type'] == 'response.audio_transcript.done':
                            transcript = response.get('transcript', '')
                            if transcript:
                                logger.info(f"🤖 AI completed: {transcript}")
                                
                        elif response['type'] == 'error':
                            logger.error(f"❌ OpenAI error: {response.get('error', {})}")
                            
                except Exception as e:
                    logger.error(f"❌ Error in OpenAI handler: {e}")
            
            # Run both tasks concurrently
            logger.info("🚀 Starting bidirectional audio streaming...")
            await asyncio.gather(
                forward_twilio_to_openai(),
                forward_openai_to_twilio()
            )
            
    except Exception as e:
        logger.error(f"❌ Error in media_stream handler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("🔌 WebSocket connection closed")

@app.get("/test-openai")
async def test_openai_connection():
    """Test OpenAI Realtime API connection from deployed server"""
    import asyncio
    import websockets
    import json
    
    try:
        logger.info("🧪 Testing OpenAI Realtime API connection...")
        
        if not OPENAI_API_KEY:
            return {"error": "OPENAI_API_KEY not found", "status": "failed"}
        
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        async with websockets.connect(url, additional_headers=headers) as ws:
            logger.info("✅ Connected to OpenAI Realtime API")
            
            # Send session config
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "You are a helpful spa booking assistant.",
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "voice": "alloy",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
                    "temperature": 0.7
                }
            }
            
            await ws.send(json.dumps(session_config))
            logger.info("📋 Session configuration sent")
            
            # Wait for response
            response = await ws.recv()
            data = json.loads(response)
            
            if data['type'] == 'session.updated':
                logger.info("✅ Session configured successfully")
                return {
                    "status": "success",
                    "message": "OpenAI Realtime API is ready for Twilio integration",
                    "session_updated": True
                }
            else:
                logger.error(f"❌ Unexpected response: {data}")
                return {
                    "status": "failed",
                    "message": f"Unexpected response: {data['type']}",
                    "response": data
                }
                
    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code == 401:
            logger.error("❌ Authentication failed - check API key")
            return {"status": "failed", "error": "Authentication failed - check API key"}
        elif e.status_code == 404:
            logger.error("❌ Model not found - check account access")
            return {"status": "failed", "error": "Model not found - check account access"}
        else:
            logger.error(f"❌ HTTP {e.status_code}: {e}")
            return {"status": "failed", "error": f"HTTP {e.status_code}: {e}"}
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"❌ Connection closed: {e}")
        return {"status": "failed", "error": f"Connection closed: {e}"}
    except Exception as e:
        logger.error(f"❌ OpenAI connection failed: {e}")
        return {"status": "failed", "error": str(e)}

@app.post("/api/function-handler")
async def function_handler(request: Request):
    """Handle function calls from OpenAI assistant"""
    try:
        data = await request.json()
        function_name = data.get('function_name')
        arguments = data.get('arguments', {})
        context = data.get('context', {})
        
        logger.info(f"Function call received: {function_name}")
        
        # Auto-add phone from Twilio call metadata
        if 'phone_number' not in arguments:
            phone = (context.get('from') or 
                    context.get('customer_phone') or 
                    context.get('caller_phone') or
                    arguments.get('customer_phone'))
            if phone:
                arguments['phone_number'] = phone
                logger.info(f"Using phone number from Twilio: {phone}")
        
        # For now, return a simple response
        # TODO: Implement actual Supabase integration
        if function_name == 'check_slot_availability':
            return {
                "available": True,
                "message": "Slot available with 13 spots remaining",
                "spots_remaining": 13
            }
        elif function_name == 'book_spa_slot':
            return {
                "success": True,
                "message": "Booking confirmed",
                "booking_reference": "SPA-123456"
            }
        elif function_name == 'get_latest_appointment':
            return {
                "found": False,
                "message": "No appointments found"
            }
        elif function_name == 'delete_appointment':
            return {
                "success": True,
                "message": "Appointment cancelled"
            }
        else:
            return {"error": "Unknown function"}
        
    except Exception as e:
        logger.error(f"Error in function handler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting spa booking system on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)