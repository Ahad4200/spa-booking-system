"""
Raw WebSocket server for Twilio Media Streams.
Handles bidirectional audio streaming between Twilio and OpenAI Realtime API.
"""

import logging
import json
import asyncio
import websockets
from config import Config

logger = logging.getLogger(__name__)

class TwilioMediaStreamHandler:
    """Handles WebSocket connection for Twilio Media Streams"""
    
    def __init__(self):
        self.openai_ws = None
        self.stream_sid = None
        self.call_sid = None
        self.openai_task = None
        
    async def handle(self, ws):
        """Main handler for Twilio WebSocket connection"""
        logger.info("New Twilio Media Stream WebSocket connection")
        
        try:
            # Connect to OpenAI
            await self._connect_to_openai()
            
            # Handle messages
            async for message in ws:
                await self._process_message(message, ws)
                
        except Exception as e:
            logger.error(f"WebSocket handler error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()
    
    async def _connect_to_openai(self):
        """Connect to OpenAI Realtime API"""
        try:
            url = f"wss://api.openai.com/v1/realtime?model={Config.OPENAI_MODEL}"
            headers = {
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            logger.info("Connecting to OpenAI Realtime API...")
            self.openai_ws = await websockets.connect(url, extra_headers=headers)
            
            # Configure session
            await self._configure_session()
            
            # Start listening to OpenAI responses
            self.openai_task = asyncio.create_task(self._listen_to_openai())
            
            logger.info("Successfully connected to OpenAI")
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI: {str(e)}")
            raise
    
    async def _configure_session(self):
        """Configure OpenAI session"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self._get_instructions(),
                "voice": "alloy",
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "temperature": 0.8
            }
        }
        
        await self.openai_ws.send(json.dumps(config))
        logger.info("Sent session configuration to OpenAI")
    
    def _get_instructions(self):
        """Get AI assistant instructions"""
        slots = "\n".join([f"  - {s['display']}" for s in Config.TIME_SLOTS])
        return f"""You are a professional receptionist for {Config.SPA_NAME}, a luxury spa in Italy.

Operating hours: 10:00 AM to 8:00 PM daily
Session duration: {Config.SESSION_DURATION_HOURS} hours  
Max capacity: {Config.MAX_CAPACITY_PER_SLOT} people per slot

AVAILABLE SLOTS:
{slots}

CONVERSATION FLOW:
1. Greet in Italian or English
2. Confirm phone number
3. Ask for name
4. Ask for preferred date
5. Present available slots
6. Check availability and book
7. Confirm booking details

Be friendly, patient, and professional."""
    
    async def _process_message(self, message, twilio_ws):
        """Process incoming message from Twilio"""
        try:
            data = json.loads(message)
            event = data.get('event')
            
            if event == 'start':
                await self._handle_start(data)
            elif event == 'media':
                await self._handle_media(data)
            elif event == 'stop':
                await self._handle_stop()
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    async def _handle_start(self, data):
        """Handle stream start"""
        self.stream_sid = data['start']['streamSid']
        self.call_sid = data['start']['callSid']
        logger.info(f"Stream started: {self.stream_sid}, Call: {self.call_sid}")
    
    async def _handle_media(self, data):
        """Handle incoming audio from Twilio"""
        if self.openai_ws:
            payload = data['media']['payload']
            audio_msg = {
                "type": "input_audio_buffer.append",
                "audio": payload
            }
            await self.openai_ws.send(json.dumps(audio_msg))
    
    async def _handle_stop(self):
        """Handle stream stop"""
        logger.info(f"Stream stopped: {self.stream_sid}")
        await self._cleanup()
    
    async def _listen_to_openai(self):
        """Listen for responses from OpenAI"""
        try:
            async for message in self.openai_ws:
                data = json.loads(message)
                await self._process_openai_message(data)
        except Exception as e:
            logger.error(f"Error listening to OpenAI: {str(e)}")
    
    async def _process_openai_message(self, data):
        """Process message from OpenAI"""
        event_type = data.get('type')
        
        if event_type == 'response.audio.delta':
            # Audio response from AI
            logger.debug("Received audio from OpenAI")
        elif event_type == 'response.audio_transcript.delta':
            logger.info(f"AI: {data.get('delta', '')}")
        elif event_type == 'error':
            logger.error(f"OpenAI error: {data.get('error', {})}")
    
    async def _cleanup(self):
        """Cleanup connections"""
        if self.openai_task:
            self.openai_task.cancel()
        if self.openai_ws:
            await self.openai_ws.close()
        logger.info("Cleaned up connections")

