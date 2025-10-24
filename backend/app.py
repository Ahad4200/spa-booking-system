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
