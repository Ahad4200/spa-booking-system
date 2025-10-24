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
SYSTEM_MESSAGE = """You are Sara, a friendly spa receptionist at Santa Caterina Beauty Farm. 
Keep responses concise and natural. Help with massage bookings. 
Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Caller's phone: {{from}}"""

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
    """Handle Twilio Media Streams - CORRECT IMPLEMENTATION"""
    logger.info("📞 WebSocket connection attempted")
    
    try:
        await websocket.accept()
        logger.info("✅ WebSocket accepted")
    except Exception as e:
        logger.error(f"❌ Failed to accept: {e}")
        return
    
    stream_sid = None
    start_received = False
    
    try:
        # CRITICAL: Iterate through ALL messages as text
        async for message in websocket.iter_text():
            data = json.loads(message)
            event_type = data.get('event')
            
            logger.info(f"📨 Event: {event_type}")
            
            # ===== HANDLE START EVENT =====
            if event_type == 'start' and not start_received:
                start_received = True
                stream_sid = data['start'].get('streamSid')
                logger.info(f"✅ Start event received, streamSid: {stream_sid}")
                
                # Only NOW connect to OpenAI
                asyncio.create_task(
                    handle_openai_connection(websocket, stream_sid)
                )
                continue
            
            # ===== HANDLE MEDIA EVENT =====
            if event_type == 'media' and start_received:
                audio_payload = data['media'].get('payload')
                logger.info(f"🔊 Audio received: {len(audio_payload)} bytes")
                # Forward to OpenAI (implement separately)
                
            # ===== HANDLE STOP EVENT =====
            elif event_type == 'stop':
                logger.info(f"📞 Stop event received")
                break
                
    except WebSocketDisconnect:
        logger.info("❌ WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ Error in media_stream: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await websocket.close()
        except:
            pass


async def handle_openai_connection(twilio_ws: WebSocket, stream_sid: str):
    """Connect to OpenAI AFTER Twilio handshake completes"""
    logger.info("🔌 Connecting to OpenAI...")
    
    try:
        async with websockets.connect(
            "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17",
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            logger.info("✅ Connected to OpenAI")
            
            # Send session config
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
            
            # Now handle bidirectional audio streaming
            await asyncio.gather(
                forward_twilio_to_openai(twilio_ws, openai_ws, stream_sid),
                forward_openai_to_twilio(twilio_ws, openai_ws, stream_sid)
            )
            
    except Exception as e:
        logger.error(f"❌ OpenAI connection failed: {e}")
        import traceback
        traceback.print_exc()


async def forward_twilio_to_openai(twilio_ws: WebSocket, openai_ws, stream_sid: str):
    """Forward audio from Twilio to OpenAI"""
    try:
        async for message in twilio_ws.iter_text():
            data = json.loads(message)
            event = data.get('event')
            
            if event == 'media':
                # Forward audio to OpenAI
                audio_payload = data['media']['payload']
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_payload
                }
                await openai_ws.send(json.dumps(audio_append))
                logger.info(f"🔊 Forwarded audio to OpenAI: {len(audio_payload)} bytes")
                
            elif event == 'stop':
                logger.info("📞 Call ended")
                break
                
    except Exception as e:
        logger.error(f"❌ Error forwarding to OpenAI: {e}")


async def forward_openai_to_twilio(twilio_ws: WebSocket, openai_ws, stream_sid: str):
    """Forward audio from OpenAI to Twilio"""
    try:
        async for message in openai_ws:
            response = json.loads(message)
            
            if response['type'] == 'session.updated':
                logger.info("✅ OpenAI session updated")
                
            elif response['type'] == 'response.audio.delta':
                # Forward audio response to Twilio
                if response.get('delta') and stream_sid:
                    audio_payload = base64.b64encode(
                        base64.b64decode(response['delta'])
                    ).decode('utf-8')
                    
                    audio_message = {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": audio_payload
                        }
                    }
                    await twilio_ws.send_json(audio_message)
                    logger.info(f"🔊 Forwarded audio to Twilio: {len(audio_payload)} bytes")
                    
            elif response['type'] == 'input_audio_buffer.speech_started':
                logger.info("🎤 User started speaking")
                
            elif response['type'] == 'response.audio_transcript.done':
                transcript = response.get('transcript', '')
                logger.info(f"🤖 AI said: {transcript}")
                
    except Exception as e:
        logger.error(f"❌ Error forwarding to Twilio: {e}")

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
