"""
Spa Booking System - FastAPI implementation with CORRECT Twilio Media Streams handling
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

# Environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
VOICE = "alloy"

def get_system_message(customer_phone):
    # Render all values before injecting into the prompt!
    return f"""# Role
You are Sara, a warm and professional AI receptionist for {Config.SPA_NAME}, a luxury wellness spa in Italy. You handle phone bookings with grace, patience, and efficiency.

# Context
- Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- Caller's phone: {customer_phone} (automatically provided - NEVER ask for it)
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
- Call: get_latest_appointment({{{{from}}}})
- If found: "Ho trovato la sua prenotazione per il [date] alle [time]. Desidera altro?"
- If not found: "Non trovo prenotazioni con questo numero. Vuole prenotarne una nuova?"

## 3. CANCELLATION Flow
**Step 1 - Find Appointment**
- Call: get_latest_appointment({{{{from}}}})
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
- Phone number is AUTOMATICALLY provided - NEVER ask for it
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
   - Use phone: {{{{from}}}}

4. **delete_appointment(phone_number, booking_reference)**
   - Cancels an appointment
   - ONLY use after explicit confirmation

# Common Scenarios

**"What services do you offer?"**
"Offriamo sessioni spa di 2 ore con accesso completo alle nostre strutture wellness. Per informazioni dettagliate sui trattamenti specifici, può visitare il nostro sito web o chiedere alla reception."

**"How much does it cost?"**
"Per i prezzi aggiornati, la invito a consultare il nostro sito web o contattare la reception. Posso però aiutarla a prenotare il suo appuntamento."

**"Can I book for multiple people?"**
"Certo! Mi dica per quante persone e verifico la disponibilità. Ricordi che ogni slot può ospitare massimo {Config.MAX_CAPACITY_PER_SLOT} persone."

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

# Assuming you receive the caller's phone from Twilio metadata as "from"
customer_phone = event.get("from")  # or however you extract it from the Twilio event

SYSTEM_MESSAGE = get_system_message(customer_phone=customer_phone)

session_config = {
    "type": "session.update",
    "session": {
        "modalities": ["text", "audio"],
        "input_audio_format": "g711_ulaw",
        "output_audio_format": "g711_ulaw",
        "voice": VOICE,
        "instructions": SYSTEM_MESSAGE,
        "temperature": 0.7,
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500
        }
    }
}


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
    # Convert https:// to wss:// for WebSocket connections
    websocket_url = base_url.replace("https://", "wss://") + "/media-stream"
    
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{websocket_url}" />
    </Connect>
</Response>'''
    
    logger.info(f"📞 Returning TwiML with WebSocket URL: {websocket_url}")
    return Response(content=twiml, media_type="application/xml")

@app.websocket("/media-stream")
async def media_stream_handler(websocket: WebSocket):
    """Handle Twilio Media Streams - CORRECT IMPLEMENTATION with proper event sequence"""
    logger.info("📞 WebSocket connection attempted")
    
    try:
        await websocket.accept()
        logger.info("✅ WebSocket accepted")
    except Exception as e:
        logger.error(f"❌ Failed to accept: {e}")
        return
    
    try:
        # CRITICAL: Connect to OpenAI BEFORE processing Twilio events
        openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
        
        async with websockets.connect(
            openai_url,
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            logger.info("✅ Connected to OpenAI Realtime API")
            
            # Initialize OpenAI session immediately
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": SYSTEM_MESSAGE,
                    "voice": VOICE,
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
            logger.info("✅ OpenAI session configured")
            
            stream_sid = None
            
            # Task 1: Receive from Twilio and forward to OpenAI
            async def receive_from_twilio():
                nonlocal stream_sid
                try:
                    async for message in websocket.iter_text():
                        try:
                            data = json.loads(message)
                            event_type = data.get('event')
                            
                            logger.info(f"📨 Event received: {event_type}")
                            
                            # Handle connected event (protocol handshake)
                            if event_type == 'connected':
                                logger.info("✅ Twilio protocol connected")
                                continue
                            
                            # Handle start event (stream initialization)
                            elif event_type == 'start':
                                stream_sid = data['start'].get('streamSid')
                                logger.info(f"✅ Start event received, streamSid: {stream_sid}")
                                continue
                            
                            # Handle media events (audio packets)
                            elif event_type == 'media' and stream_sid:
                                audio_payload = data['media']['payload']
                                audio_append = {
                                    "type": "input_audio_buffer.append",
                                    "audio": audio_payload
                                }
                                await openai_ws.send(json.dumps(audio_append))
                                logger.info(f"🔊 Forwarded audio to OpenAI: {len(audio_payload)} bytes")
                            
                            # Handle stop event (stream termination)
                            elif event_type == 'stop':
                                logger.info("📞 Stream stopped")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON from Twilio: {e}")
                            continue
                            
                except WebSocketDisconnect:
                    logger.info("❌ Twilio WebSocket disconnected")
                except Exception as e:
                    logger.error(f"Error in receive_from_twilio: {e}", exc_info=True)
            
            # Task 2: Receive from OpenAI and forward to Twilio
            async def send_to_twilio():
                try:
                    async for openai_message in openai_ws:
                        try:
                            response = json.loads(openai_message)
                            response_type = response.get('type')
                            
                            if response_type == 'session.updated':
                                logger.info("✅ OpenAI session updated")
                                
                            elif response_type == 'response.audio.delta' and stream_sid:
                                # Forward audio response to Twilio
                                audio_delta = response.get('delta', '')
                                if audio_delta:
                                    audio_message = {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {
                                            "payload": audio_delta
                                        }
                                    }
                                    await websocket.send_json(audio_message)
                                    logger.info(f"🔊 Forwarded audio to Twilio: {len(audio_delta)} bytes")
                            
                            elif response_type == 'input_audio_buffer.speech_started':
                                logger.info("🎤 User started speaking")
                                
                            elif response_type == 'response.audio_transcript.done':
                                transcript = response.get('transcript', '')
                                logger.info(f"🤖 AI said: {transcript}")
                                
                        except Exception as e:
                            logger.error(f"Error processing OpenAI message: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error in send_to_twilio: {e}", exc_info=True)
            
            # Run both tasks concurrently
            await asyncio.gather(receive_from_twilio(), send_to_twilio())
            
    except Exception as e:
        logger.error(f"❌ Error in media_stream_handler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await websocket.close()
        except:
            pass

# Function handler for AI tools
@app.post("/api/function-handler")
async def function_handler(request: Request):
    """Handle function calls from OpenAI"""
    try:
        data = await request.json()
        function_name = data.get("function_name")
        arguments = data.get("arguments", {})
        
        logger.info(f"🔧 Function call: {function_name}")
        
        if function_name == "get_latest_appointment":
            # Implementation for getting latest appointment
            return {
                "found": False,
                "message": "No appointments found"
            }
        elif function_name == "delete_appointment":
            # Implementation for deleting appointment
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
