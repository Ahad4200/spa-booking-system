"""
Main Flask application for the spa booking system.
Handles incoming calls and coordinates between Twilio, OpenAI, and Supabase.
"""

import logging
import json
import asyncio
import websockets
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock
from config import Config
from handlers.twilio_handler import TwilioHandler
from handlers.openai_handler import OpenAIHandler
from handlers.supabase_handler import SupabaseHandler
from conversation_logger import conversation_logger

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app, origins=['*'])

# Initialize WebSocket support
sock = Sock(app)

# Validate configuration on startup
Config.validate()

# Initialize handlers (lazy loading)
twilio_handler = None
openai_handler = None
supabase_handler = None

def get_twilio_handler():
    global twilio_handler
    if twilio_handler is None:
        twilio_handler = TwilioHandler()
    return twilio_handler

def get_openai_handler():
    global openai_handler
    if openai_handler is None:
        openai_handler = OpenAIHandler()
    return openai_handler

def get_supabase_handler():
    global supabase_handler
    if supabase_handler is None:
        supabase_handler = SupabaseHandler()
    return supabase_handler

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Spa Booking System',
        'version': '1.0.0'
    })

@app.route('/test-db', methods=['GET'])
def test_database():
    """Test database connection"""
    try:
        # Test basic table access
        result = get_supabase_handler().client.table('spa_bookings').select('id').limit(1).execute()
        return jsonify({
            'status': 'success',
            'message': 'Supabase connection successful',
            'database': 'reachable',
            'tables': 'accessible',
            'project_id': 'biaewzljhaowgaocxzxq'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Supabase connection failed',
            'error': str(e),
            'database': 'unreachable'
        }), 500

@app.route('/webhook/incoming-call', methods=['POST'])
@app.route('/webhook/voice', methods=['POST'])
def incoming_call():
    """Twilio webhook for incoming calls"""
    try:
        logger.info("Incoming call received")
        response = get_twilio_handler().handle_incoming_call(request)
        return response
    except Exception as e:
        logger.error(f"Error handling incoming call: {str(e)}")
        return str(get_twilio_handler().create_error_response()), 500

@app.route('/webhook/call-status', methods=['POST'])
def call_status():
    """Twilio webhook for call status updates"""
    try:
        call_sid = request.form.get('CallSid')
        call_status = request.form.get('CallStatus')
        duration = request.form.get('Duration')
        
        logger.info(f"Call status update: {call_sid} - {call_status}")
        
        # Update call session in database
        get_supabase_handler().update_call_session(call_sid, {'status': call_status})
        
        # End conversation logging if call completed
        if call_status in ['completed', 'busy', 'no-answer', 'failed']:
            conversation_logger.end_session(call_sid, call_status)
        
        return '', 200
    except Exception as e:
        logger.error(f"Error updating call status: {str(e)}")
        return '', 500

@app.route('/api/function-handler', methods=['POST'])
def function_handler():
    """Handle function calls from OpenAI assistant"""
    try:
        data = request.json
        function_name = data.get('function_name')
        arguments = data.get('arguments', {})
        context = data.get('context', {})
        
        logger.info(f"Function call received: {function_name}")
        
        # Route to appropriate handler
        if function_name == 'check_slot_availability':
            result = get_supabase_handler().check_slot_availability(
                arguments['date'],
                arguments['start_time']
            )
        elif function_name == 'book_spa_slot':
            # Map arguments to expected format
            booking_data = {
                'name': arguments.get('customer_name'),
                'phone': context.get('customer_phone') or arguments.get('customer_phone'),
                'date': arguments.get('booking_date'),
                'start_time': arguments.get('slot_start_time') or arguments.get('start_time'),
                'end_time': arguments.get('slot_end_time') or arguments.get('end_time')
            }
            result = get_supabase_handler().book_spa_slot(booking_data)
        else:
            return jsonify({'error': 'Unknown function'}), 400
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in function handler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings/<date>', methods=['GET'])
def get_bookings(date):
    """Get all bookings for a specific date (admin endpoint)"""
    try:
        bookings = get_supabase_handler().get_bookings_for_date(date)
        return jsonify(bookings)
    except Exception as e:
        logger.error(f"Error fetching bookings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

# WebSocket endpoint for Twilio Media Streams
@sock.route('/media-stream')
def media_stream(ws):
    """Bridge Twilio Media Stream ↔ OpenAI Realtime API"""
    logger.info("✅ Twilio Media Stream WebSocket connected")
    
    stream_sid = None
    call_sid = None
    openai_ws = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def connect_to_openai_with_retry(max_retries=3):
        """Connect to OpenAI with automatic retry"""
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Attempting OpenAI connection (attempt {attempt + 1}/{max_retries})")
                ws_conn = await websockets.connect(
                    f"wss://api.openai.com/v1/realtime?model={Config.OPENAI_MODEL}",
                    extra_headers={
                        "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                        "OpenAI-Beta": "realtime=v1"
                    }
                )
                logger.info("✅ OpenAI connection established")
                return ws_conn
            except Exception as e:
                logger.error(f"❌ OpenAI connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
                else:
                    raise
    
    async def bridge_audio():
        """Bridge audio between Twilio and OpenAI"""
        nonlocal openai_ws
        
        try:
            # Connect to OpenAI with retry
            openai_ws = await connect_to_openai_with_retry()
            
            # Send session configuration to OpenAI
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "voice": "alloy",
                    "instructions": f"""You are a professional receptionist for {Config.SPA_NAME}, a luxury spa in Italy.

Operating hours: 10:00 AM to 8:00 PM daily
Session duration: {Config.SESSION_DURATION_HOURS} hours  
Max capacity: {Config.MAX_CAPACITY_PER_SLOT} people per slot

CONVERSATION FLOW:
1. Greet in Italian or English
2. Confirm phone number
3. Ask for name
4. Ask for preferred date
5. Present available slots
6. Check availability and book
7. Confirm booking details

Be friendly, patient, and professional. Keep responses concise and natural.""",
                    "temperature": 0.7,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }
            }
            
            await openai_ws.send(json.dumps(session_config))
            logger.info("📋 Session configuration sent to OpenAI")
            
            # Start keepalive task
            keepalive_task = asyncio.create_task(send_keepalive(openai_ws))
            
            # Handle bidirectional audio streaming
            while openai_ws and not ws.closed:
                try:
                    # Receive from Twilio (non-blocking)
                    try:
                        twilio_message = ws.receive(timeout=0.1)
                        if twilio_message:
                            data = json.loads(twilio_message)
                            
                            if data['event'] == 'media':
                                # Forward audio to OpenAI
                                audio_payload = data['media']['payload']
                                logger.debug(f"🔊 Forwarding {len(audio_payload)} bytes to OpenAI")
                                
                                await openai_ws.send(json.dumps({
                                    "type": "input_audio_buffer.append",
                                    "audio": audio_payload
                                }))
                    except:
                        pass  # No message from Twilio
                    
                    # Receive from OpenAI (non-blocking)
                    try:
                        openai_message = await asyncio.wait_for(
                            openai_ws.recv(),
                            timeout=0.1
                        )
                        openai_data = json.loads(openai_message)
                        
                        if openai_data['type'] == 'response.audio.delta':
                            # Forward audio response to Twilio
                            logger.debug(f"🎤 Sending {len(openai_data['delta'])} bytes to Twilio")
                            ws.send(json.dumps({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": openai_data['delta']
                                }
                            }))
                        elif openai_data['type'] == 'response.audio_transcript.delta':
                            logger.info(f"🤖 AI: {openai_data.get('delta', '')}")
                        elif openai_data['type'] == 'error':
                            logger.error(f"❌ OpenAI error: {openai_data.get('error', {})}")
                            
                    except asyncio.TimeoutError:
                        pass  # No message from OpenAI
                        
                except Exception as e:
                    logger.error(f"❌ Bridge error: {e}")
                    break
            
            # Cancel keepalive task
            keepalive_task.cancel()
        
        except Exception as e:
            logger.error(f"❌ OpenAI connection error: {e}")
        finally:
            if openai_ws:
                await openai_ws.close()
                logger.info("🔌 OpenAI connection closed")
    
    async def send_keepalive(openai_ws):
        """Send periodic keepalive to OpenAI"""
        while True:
            try:
                await asyncio.sleep(20)  # Every 20 seconds
                await openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.commit"
                }))
                logger.debug("💓 Keepalive sent to OpenAI")
            except:
                break
    
    try:
        while True:
            # Receive message from Twilio
            message = ws.receive()
            if message is None:
                break
            
            data = json.loads(message)
            event = data.get('event')
            
            if event == 'start':
                stream_sid = data['start'].get('streamSid')
                call_sid = data['start'].get('callSid')
                logger.info(f"📞 Call started: {stream_sid}, Call: {call_sid}")
                
                # Start the OpenAI bridge
                loop.run_until_complete(bridge_audio())
                
            elif event == 'stop':
                logger.info(f"📞 Call ended: {stream_sid}")
                break
                
    except Exception as e:
        logger.error(f"❌ WebSocket ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("WebSocket closed")
        ws.close()

if __name__ == '__main__':
    logger.info(f"Starting spa booking system on port {Config.FLASK_PORT}")
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.DEBUG
    )