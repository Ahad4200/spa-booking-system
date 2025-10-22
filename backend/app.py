"""
Main Flask application for the spa booking system.
Handles incoming calls and coordinates between Twilio, OpenAI, and Supabase.
"""

import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
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
CORS(app, origins=['*'])

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

if __name__ == '__main__':
    logger.info(f"Starting spa booking system on port {Config.FLASK_PORT}")
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.DEBUG
    )