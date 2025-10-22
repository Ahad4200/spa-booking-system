"""
Twilio handler for managing phone calls and WebSocket connections.
"""

import logging
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from twilio.rest import Client
from config import Config
from .supabase_handler import SupabaseHandler
from conversation_logger import conversation_logger

logger = logging.getLogger(__name__)

class TwilioHandler:
    def __init__(self):
        self.client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        self.supabase = SupabaseHandler()
    
    def handle_incoming_call(self, request):
        """Process incoming call and establish WebSocket connection to OpenAI"""
        try:
            # Extract caller information
            caller_phone = request.form.get('From')
            call_sid = request.form.get('CallSid')
            caller_country = request.form.get('FromCountry', 'IT')
            
            logger.info(f"Incoming call from {caller_phone} (Call SID: {call_sid})")
            
            # Start conversation logging
            conversation_logger.start_session(call_sid, caller_phone)
            
            # Store call session
            session_id = self.supabase.create_call_session({
                'phone_number': self._format_phone_number(caller_phone),
                'call_id': call_sid,
                'country': caller_country,
                'status': 'connecting'
            })
            
            # Create TwiML response
            response = VoiceResponse()
            
            # Add initial greeting while connecting
            response.say(
                f"Benvenuto a {Config.SPA_NAME}. Un momento per favore...",
                voice='alice',
                language='it-IT'
            )
            
            # Connect to OpenAI Realtime
            connect = Connect()
            stream = connect.stream(
                url=f"wss://api.openai.com/v1/realtime?model={Config.OPENAI_MODEL}"
            )
            
            # Add custom parameters
            stream.parameter(name='customer_phone', value=caller_phone)
            stream.parameter(name='call_sid', value=call_sid)
            stream.parameter(name='session_id', value=session_id)
            
            response.append(connect)
            
            return str(response)
            
        except Exception as e:
            logger.error(f"Error in handle_incoming_call: {str(e)}")
            return str(self.create_error_response())
    
    def _format_phone_number(self, phone_number):
        """Format phone number for Italian standards"""
        # Remove spaces and special characters
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Ensure it starts with country code
        if not cleaned.startswith('39') and len(cleaned) == 10:
            cleaned = '39' + cleaned
        
        # Format as +39 XXX XXX XXXX
        if cleaned.startswith('39'):
            return f"+{cleaned[:2]} {cleaned[2:5]} {cleaned[5:8]} {cleaned[8:]}"
        
        return phone_number
    
    def create_error_response(self):
        """Create error response for failed connections"""
        response = VoiceResponse()
        response.say(
            "Ci scusiamo, si è verificato un errore tecnico. "
            "La preghiamo di riprovare più tardi.",
            voice='alice',
            language='it-IT'
        )
        response.hangup()
        return response
    
    def send_sms_confirmation(self, phone_number, booking_details):
        """Send SMS confirmation after successful booking"""
        try:
            message = self.client.messages.create(
                body=f"Conferma prenotazione {Config.SPA_NAME}: "
                     f"{booking_details['date']} alle {booking_details['time']}. "
                     f"Codice: {booking_details['reference']}",
                from_=Config.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            logger.info(f"SMS confirmation sent: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return False