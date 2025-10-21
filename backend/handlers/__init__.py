"""
Handlers package initialization.
Makes the handlers module importable.
"""

from .twilio_handler import TwilioHandler
from .openai_handler import OpenAIHandler
from .supabase_handler import SupabaseHandler

__all__ = [
    'TwilioHandler',
    'OpenAIHandler',
    'SupabaseHandler'
]

# Version info
__version__ = '1.0.0'