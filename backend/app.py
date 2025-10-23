"""
Main Flask application for the spa booking system.
Handles incoming calls and coordinates between Twilio, OpenAI, and Supabase.
"""

import logging
import json
import os
import time
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock
from config import Config
from handlers.twilio_handler import TwilioHandler
from handlers.openai_handler import OpenAIHandler
from handlers.supabase_handler import SupabaseHandler
from conversation_logger import conversation_logger
import websocket

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

@app.route('/debug/env')
def debug_env():
    """Debug environment variables"""
    import os
    from dotenv import load_dotenv
    
    # Load .env file
    load_dotenv()
    
    vars_to_check = [
        'OPENAI_API_KEY',
        'SUPABASE_URL', 
        'SUPABASE_KEY',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_PHONE_NUMBER'
    ]
    
    env_status = {}
    for var in vars_to_check:
        value = os.environ.get(var)
        if value:
            # Show first 10 chars for security
            masked = value[:10] + "..." if len(value) > 10 else value
            env_status[var] = f"SET ({masked})"
        else:
            env_status[var] = "NOT SET"
    
    return jsonify({
        'environment_variables': env_status,
        'python_version': os.sys.version,
        'current_directory': os.getcwd()
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
        
        # Auto-add phone from Twilio call metadata
        # The phone number comes from Twilio's {from} parameter
        if 'phone_number' not in arguments:
            # Try to get phone from Twilio call metadata
            phone = (context.get('from') or 
                    context.get('customer_phone') or 
                    context.get('caller_phone') or
                    arguments.get('customer_phone'))
            if phone:
                arguments['phone_number'] = phone
                logger.info(f"Using phone number from Twilio: {phone}")
        
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
                'name': arguments.get('customer_name') or arguments.get('name'),
                'phone': context.get('customer_phone') or arguments.get('customer_phone') or arguments.get('phone_number'),
                'date': arguments.get('booking_date') or arguments.get('date'),
                'start_time': arguments.get('slot_start_time') or arguments.get('start_time'),
                'end_time': arguments.get('slot_end_time') or arguments.get('end_time')
            }
            result = get_supabase_handler().book_spa_slot(booking_data)
        elif function_name == 'get_latest_appointment':
            result = get_supabase_handler().get_latest_appointment(
                arguments['phone_number']
            )
        elif function_name == 'delete_appointment':
            result = get_supabase_handler().delete_appointment(
                arguments['phone_number'],
                arguments.get('booking_reference')
            )
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
    """
    Twilio Media Stream ↔ OpenAI Realtime API Bridge
    Synchronous implementation with bidirectional audio streaming
    """
    stream_sid = None
    call_start_time = None
    openai_ws = None
    openai_thread = None
    audio_queue = []
    response_queue = []
    
    logger.info("✅ WebSocket connected - media_stream handler started")
    
    def on_openai_message(ws, message):
        """Handle messages from OpenAI Realtime API"""
        try:
            data = json.loads(message)
            
            if data.get('type') == 'response.audio.delta':
                # Forward audio response to Twilio
                audio_delta = data.get('delta', '')
                if audio_delta and stream_sid:
                    logger.debug(f"🎤 Sending {len(audio_delta)} bytes to Twilio")
                    ws.send(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": audio_delta
                        }
                    }))
                    
            elif data.get('type') == 'response.audio_transcript.delta':
                # Log AI transcript
                transcript = data.get('delta', '')
                if transcript:
                    logger.info(f"🤖 AI: {transcript}")
                    
            elif data.get('type') == 'error':
                logger.error(f"❌ OpenAI error: {data.get('error', {})}")
                
        except Exception as e:
            logger.error(f"❌ Error processing OpenAI message: {e}")
    
    def on_openai_error(ws, error):
        """Handle OpenAI WebSocket errors"""
        logger.error(f"❌ OpenAI WebSocket error: {error}")
    
    def on_openai_close(ws, close_status_code, close_msg):
        """Handle OpenAI WebSocket close"""
        logger.info("🔌 OpenAI WebSocket closed")
    
    def connect_to_openai():
        """Connect to OpenAI Realtime API in a separate thread"""
        nonlocal openai_ws
        
        try:
            logger.info("🔌 Connecting to OpenAI Realtime API...")
            
            # Create WebSocket connection to OpenAI
            openai_ws = websocket.WebSocketApp(
                f"wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17",
                header={
                    "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                },
                on_message=on_openai_message,
                on_error=on_openai_error,
                on_close=on_openai_close
            )
            
            # Send session configuration
            session_config = {
    "type": "session.update",
    "session": {
        "modalities": ["text", "audio"],
        "input_audio_format": "g711_ulaw",
        "output_audio_format": "g711_ulaw",
        "voice": "alloy",
        "instructions": f"""# Role
You are Sara, a warm and professional AI receptionist for {Config.SPA_NAME}, a luxury wellness spa in Italy. You handle phone bookings with grace, patience, and efficiency.

# Context
- Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')} Rome time (CEST/CET)
- Caller's phone: {{from}} (automatically provided by Twilio - NEVER ask for it)
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
- The phone number is already known - focus on helping""",
        "temperature": 0.7,
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500
        }
    }
}
            
            openai_ws.send(json.dumps(session_config))
            logger.info("📋 Session configuration sent to OpenAI")
            
            # Start keepalive in background
            def send_keepalive():
                while openai_ws and openai_ws.sock:
                    try:
                        time.sleep(20)  # Every 20 seconds
                        openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.commit"
                        }))
                        logger.debug("💓 Keepalive sent to OpenAI")
                    except:
                        break
            
            keepalive_thread = threading.Thread(target=send_keepalive, daemon=True)
            keepalive_thread.start()
            
            # Run the WebSocket
            openai_ws.run_forever()
            
        except Exception as e:
            logger.error(f"❌ OpenAI connection error: {e}")
        finally:
            if openai_ws:
                openai_ws.close()
                logger.info("🔌 OpenAI connection closed")
    
    try:
        while True:
            # This blocks until a message arrives (that's fine!)
            message = ws.receive()
            
            if message is None:
                logger.info("❌ WebSocket closed by client")
                break
            
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.error(f"❌ Invalid JSON: {message}")
                continue
            
            event = data.get('event')
            
            # ===== EVENT: START =====
            if event == 'start':
                stream_sid = data['start']['streamSid']
                call_start_time = time.time()
                logger.info(f"\n📞 ============================================")
                logger.info(f"📞 CALL STARTED")
                logger.info(f"📞 Stream SID: {stream_sid}")
                logger.info(f"📞 From: {data['start'].get('customParameters', {}).get('from', 'N/A')}")
                logger.info(f"📞 ============================================\n")
                
                # Connect to OpenAI in a separate thread
                openai_thread = threading.Thread(target=connect_to_openai, daemon=True)
                openai_thread.start()
                
                # Wait a moment for OpenAI connection
                time.sleep(2)
                
            # ===== EVENT: MEDIA (Audio Data) =====
            elif event == 'media':
                audio_payload = data['media']['payload']
                logger.debug(f"🔊 Received {len(audio_payload)} bytes of audio")
                
                # Send audio to OpenAI if connected
                if openai_ws and openai_ws.sock:
                    try:
                        openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": audio_payload
                        }))
                        logger.debug(f"🔊 Forwarded {len(audio_payload)} bytes to OpenAI")
                    except Exception as e:
                        logger.error(f"❌ Error sending audio to OpenAI: {e}")
                
            # ===== EVENT: STOP =====
            elif event == 'stop':
                call_duration = time.time() - call_start_time if call_start_time else 0
                logger.info(f"\n📞 CALL ENDED")
                logger.info(f"📞 Duration: {call_duration:.2f} seconds")
                logger.info(f"📞 Stream SID: {stream_sid}\n")
                
                # Close OpenAI connection
                if openai_ws:
                    openai_ws.close()
                break
            
            else:
                logger.warning(f"⚠️  Unknown event: {event}")
    
    except Exception as e:
        logger.error(f"❌ ERROR in media_stream handler:")
        logger.error(f"   Type: {type(e).__name__}")
        logger.error(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up OpenAI connection
        if openai_ws:
            openai_ws.close()
        logger.info("🔌 WebSocket closing...")
        ws.close()
        logger.info("✅ WebSocket closed properly")

if __name__ == '__main__':
    logger.info(f"Starting spa booking system on port {Config.FLASK_PORT}")
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.DEBUG
    )