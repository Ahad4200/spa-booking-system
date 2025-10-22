"""
Utils package initialization.
Common utilities for the spa booking system.
"""

from .phone_formatter import PhoneFormatter
from .time_slots import TimeSlotManager

__all__ = [
    'PhoneFormatter',
    'TimeSlotManager'
]

# Version info
__version__ = '1.0.0'