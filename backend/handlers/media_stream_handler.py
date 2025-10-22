"""
WebSocket handler for Twilio Media Streams to OpenAI Realtime API relay.
Handles bidirectional audio streaming between Twilio and OpenAI.
"""

import logging
import json
import base64
import asyncio
import websockets
from config import Config

logger = logging.getLogger(__name__)

class MediaStreamHandler:
    """Handles WebSocket connection between Twilio Media Streams and OpenAI Realtime API"""
    
    def __init__(self, socketio, supabase_handler):
        self.socketio = socketio
        self.supabase = supabase_handler
        self.openai_ws = None
        self.stream_sid = None
        self.call_sid = None
        
    async def handle_twilio_connection(self, sid):
        """Handle incoming WebSocket connection from Twilio Media Streams"""
        logger.info(f"New Twilio Media Stream connection: {sid}")
        
        try:
            # Connect to OpenAI Realtime API
            self.openai_ws = await self._connect_to_openai()
            
            # Set up event handlers
            self._setup_socketio_handlers(sid)
            
        except Exception as e:
            logger.error(f"Failed to establish OpenAI connection: {str(e)}")
            self.socketio.emit('error', {'message': str(e)}, room=sid)
    
    async def _connect_to_openai(self):
        """Establish WebSocket connection to OpenAI Realtime API"""
        try:
            url = f"wss://api.openai.com/v1/realtime?model={Config.OPENAI_MODEL}"
            headers = {
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            logger.info(f"Connecting to OpenAI Realtime API: {url}")
            ws = await websockets.connect(url, extra_headers=headers)
            
            # Send session configuration immediately
            await self._configure_openai_session(ws)
            
            logger.info("Successfully connected to OpenAI Realtime API")
            return ws
            
        except Exception as e:
            logger.error(f"OpenAI connection failed: {str(e)}")
            raise
    
    async def _configure_openai_session(self, ws):
        """Configure OpenAI session with instructions and voice settings"""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self._get_system_instructions(),
                "voice": "alloy",
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
                "temperature": 0.8,
                "max_response_output_tokens": 4096
            }
        }
        
        await ws.send(json.dumps(session_config))
        logger.info("Sent session configuration to OpenAI")
    
    def _get_system_instructions(self):
        """Get AI assistant instructions"""
        slots_text = "\n".join([f"  - {slot['display']}" for slot in Config.TIME_SLOTS])
        
        return f"""You are a professional and friendly receptionist for {Config.SPA_NAME}, a luxury spa in Italy.

IMPORTANT CONTEXT:
- Operating hours: 10:00 AM to 8:00 PM daily
- Each session lasts {Config.SESSION_DURATION_HOURS} hours
- Maximum capacity: {Config.MAX_CAPACITY_PER_SLOT} people per time slot

AVAILABLE TIME SLOTS:
{slots_text}

CONVERSATION FLOW:
1. Greet warmly in Italian or English based on customer's language
2. Confirm the phone number for the booking
3. Ask for their name
4. Ask for preferred date
5. Present available time slots
6. Check availability and book the slot
7. Confirm booking with date, time, and booking reference
8. Thank them for choosing {Config.SPA_NAME}

BEHAVIOR:
- Detect language from first response and continue in that language
- Be patient and repeat information if needed
- Handle dates intelligently (today, tomorrow, specific dates)
- Always offer alternatives if a slot is full
- Confirm all details before finalizing
- Be empathetic and professional"""
    
    def _setup_socketio_handlers(self, sid):
        """Set up Socket.IO event handlers for this connection"""
        
        @self.socketio.on('message', namespace='/media-stream')
        def handle_message(data):
            """Handle incoming messages from Twilio"""
            try:
                asyncio.create_task(self._process_twilio_message(data, sid))
            except Exception as e:
                logger.error(f"Error processing Twilio message: {str(e)}")
        
        @self.socketio.on('disconnect', namespace='/media-stream')
        def handle_disconnect():
            """Handle client disconnect"""
            logger.info(f"Twilio Media Stream disconnected: {sid}")
            if self.openai_ws:
                asyncio.create_task(self.openai_ws.close())
    
    async def _process_twilio_message(self, message, sid):
        """Process incoming message from Twilio Media Stream"""
        try:
            data = json.loads(message) if isinstance(message, str) else message
            event = data.get('event')
            
            if event == 'start':
                await self._handle_stream_start(data, sid)
                
            elif event == 'media':
                await self._handle_media(data)
                
            elif event == 'stop':
                await self._handle_stream_stop(data)
                
            elif event == 'mark':
                # Acknowledgment of mark sent by us
                pass
                
            else:
                logger.warning(f"Unknown event type: {event}")
                
        except Exception as e:
            logger.error(f"Error processing Twilio message: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def _handle_stream_start(self, data, sid):
        """Handle stream start event from Twilio"""
        self.stream_sid = data['start']['streamSid']
        self.call_sid = data['start']['callSid']
        custom_parameters = data['start'].get('customParameters', {})
        
        logger.info(f"Stream started - StreamSID: {self.stream_sid}, CallSID: {self.call_sid}")
        logger.info(f"Custom parameters: {custom_parameters}")
        
        # Start OpenAI response listener
        asyncio.create_task(self._listen_to_openai(sid))
    
    async def _handle_media(self, data):
        """Handle incoming audio from Twilio and forward to OpenAI"""
        try:
            payload = data['media']['payload']
            
            # Forward audio to OpenAI
            if self.openai_ws:
                audio_message = {
                    "type": "input_audio_buffer.append",
                    "audio": payload  # Already base64 encoded from Twilio
                }
                await self.openai_ws.send(json.dumps(audio_message))
                
        except Exception as e:
            logger.error(f"Error handling media: {str(e)}")
    
    async def _handle_stream_stop(self, data):
        """Handle stream stop event from Twilio"""
        logger.info(f"Stream stopped: {self.stream_sid}")
        
        if self.openai_ws:
            await self.openai_ws.close()
            self.openai_ws = None
    
    async def _listen_to_openai(self, sid):
        """Listen for responses from OpenAI and forward to Twilio"""
        try:
            async for message in self.openai_ws:
                data = json.loads(message)
                event_type = data.get('type')
                
                if event_type == 'response.audio.delta':
                    # Forward audio to Twilio
                    await self._send_audio_to_twilio(data['delta'], sid)
                    
                elif event_type == 'response.audio_transcript.delta':
                    # Log transcript
                    logger.info(f"AI: {data.get('delta', '')}")
                    
                elif event_type == 'input_audio_buffer.speech_started':
                    logger.info("User started speaking")
                    # Optionally interrupt AI output
                    
                elif event_type == 'response.function_call_arguments.done':
                    # Handle function calls (booking, availability check)
                    await self._handle_function_call(data)
                    
                elif event_type == 'error':
                    logger.error(f"OpenAI error: {data.get('error', {})}")
                    
        except Exception as e:
            logger.error(f"Error listening to OpenAI: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def _send_audio_to_twilio(self, audio_delta, sid):
        """Send audio response from OpenAI to Twilio"""
        try:
            twilio_message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_delta  # Already base64 encoded from OpenAI
                }
            }
            
            self.socketio.emit('message', json.dumps(twilio_message), room=sid, namespace='/media-stream')
            
        except Exception as e:
            logger.error(f"Error sending audio to Twilio: {str(e)}")
    
    async def _handle_function_call(self, data):
        """Handle function calls from OpenAI (booking, availability)"""
        function_name = data.get('name')
        arguments = json.loads(data.get('arguments', '{}'))
        
        logger.info(f"Function call: {function_name} with args: {arguments}")
        
        # Handle the function call and send result back to OpenAI
        # Implementation depends on your specific functions
        
        # Send function result back
        result_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": data.get('call_id'),
                "output": json.dumps({"success": True})
            }
        }
        
        if self.openai_ws:
            await self.openai_ws.send(json.dumps(result_message))

