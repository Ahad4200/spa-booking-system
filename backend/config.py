"""
Configuration management for the spa booking system.
Centralizes all configuration and environment variables.
"""

import os
from datetime import time
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Flask Configuration
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    DEBUG = FLASK_ENV == 'development'
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
    OPENAI_MODEL = 'gpt-4o-realtime-preview'
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
    
    # Application URLs
    BASE_URL = os.getenv('BASE_URL', f'http://localhost:{FLASK_PORT}')
    
    # Spa Business Configuration
    SPA_NAME = os.getenv('SPA_NAME', 'Santa Caterina Beauty Farm')
    MAX_CAPACITY_PER_SLOT = int(os.getenv('MAX_CAPACITY_PER_SLOT', 14))
    SESSION_DURATION_HOURS = int(os.getenv('SESSION_DURATION_HOURS', 2))
    
    # Time Slots Configuration
    TIME_SLOTS = [
        {'start': '10:00:00', 'end': '12:00:00', 'display': '10:00 AM - 12:00 PM'},
        {'start': '12:00:00', 'end': '14:00:00', 'display': '12:00 PM - 2:00 PM'},
        {'start': '14:00:00', 'end': '16:00:00', 'display': '2:00 PM - 4:00 PM'},
        {'start': '16:00:00', 'end': '18:00:00', 'display': '4:00 PM - 6:00 PM'},
        {'start': '18:00:00', 'end': '20:00:00', 'display': '6:00 PM - 8:00 PM'}
    ]
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present"""
        required_vars = [
            'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
            'OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY'
        ]
        
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True