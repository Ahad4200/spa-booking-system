"""
Debug version of app.py with simplified WebSocket handler
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

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "service": "Spa Booking System",
        "status": "healthy",
        "version": "1.0.0"
    })

@app.route('/webhook/incoming-call', methods=['POST'])
def incoming_call():
    """Handle incoming Twilio calls"""
    logger.info("📞 Incoming call webhook received")
    
    # Get call details
    call_sid = request.form.get('CallSid')
    caller_phone = request.form.get('From')
    
    logger.info(f"📞 Call SID: {call_sid}, Caller: {caller_phone}")
    
    # Return TwiML response
    from twilio.twiml import VoiceResponse
    response = VoiceResponse()
    
    # Greet in Italian
    response.say("Benvenuto a Santa Caterina Beauty Farm. Un momento per favore...", 
                 language="it-IT", voice="alice")
    
    # Connect to WebSocket
    from twilio.twiml import Connect, Stream
    connect = Connect()
    stream = Stream(url="wss://spa-booking-system.onrender.com/media-stream")
    stream.parameter(name='customer_phone', value=caller_phone)
    stream.parameter(name='call_sid', value=call_sid)
    stream.parameter(name='session_id', value=f"debug-{call_sid}")
    connect.append(stream)
    response.append(connect)
    
    return str(response)

@app.route('/webhook/call-status', methods=['POST'])
def call_status():
    """Handle call status updates"""
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus')
    logger.info(f"📞 Call status update: {call_sid} -> {call_status}")
    return "OK"

# SIMPLIFIED WebSocket handler for debugging
@sock.route('/media-stream')
def media_stream(ws):
    """Simplified WebSocket handler for debugging"""
    logger.info("✅ WebSocket connected (debug version)")
    
    try:
        # Simple message loop
        while True:
            try:
                # Receive message
                message = ws.receive()
                if message is None:
                    break
                
                logger.info(f"📥 Received message: {message}")
                
                # Parse message
                try:
                    data = json.loads(message)
                    event = data.get('event')
                    logger.info(f"📊 Event: {event}")
                    
                    if event == 'start':
                        stream_sid = data.get('start', {}).get('streamSid')
                        call_sid = data.get('start', {}).get('callSid')
                        logger.info(f"📞 Stream started: {stream_sid}, Call: {call_sid}")
                        
                        # Send acknowledgment
                        response = {
                            "event": "ack",
                            "message": "Stream started successfully"
                        }
                        ws.send(json.dumps(response))
                        logger.info("📤 Sent acknowledgment")
                        
                    elif event == 'media':
                        audio_payload = data.get('media', {}).get('payload')
                        logger.info(f"🔊 Audio received: {len(audio_payload) if audio_payload else 0} bytes")
                        
                        # Send acknowledgment
                        response = {
                            "event": "ack",
                            "message": "Audio received"
                        }
                        ws.send(json.dumps(response))
                        logger.info("📤 Sent audio acknowledgment")
                        
                    elif event == 'stop':
                        logger.info("📞 Stream stopped")
                        break
                        
                    else:
                        logger.info(f"❓ Unknown event: {event}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    logger.error(f"📄 Raw message: {message}")
                    
            except Exception as e:
                logger.error(f"❌ Message processing error: {e}")
                break
                
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("🔌 WebSocket closed")
        ws.close()

if __name__ == '__main__':
    logger.info(f"Starting debug spa booking system on port {Config.FLASK_PORT}")
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.DEBUG
    )
