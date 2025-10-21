"""
Time slot management utilities.
"""

from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple
from config import Config

class TimeSlotManager:
    @staticmethod
    def get_available_slots() -> List[Dict]:
        """Get all configured time slots"""
        return Config.TIME_SLOTS
    
    @staticmethod
    def parse_time(time_str: str) -> time:
        """Parse time string to time object"""
        formats = ['%H:%M:%S', '%H:%M', '%I:%M %p', '%I:%M%p']
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse time: {time_str}")
    
    @staticmethod
    def format_time_display(time_obj: time, italian: bool = False) -> str:
        """Format time for display"""
        if italian:
            return time_obj.strftime('%H:%M')
        else:
            return time_obj.strftime('%-I:%M %p')
    
    @staticmethod
    def get_slot_by_start_time(start_time: str) -> Dict:
        """Get slot configuration by start time"""
        for slot in Config.TIME_SLOTS:
            if slot['start'] == start_time or slot['start'].startswith(start_time):
                return slot
        return None
    
    @staticmethod
    def calculate_end_time(start_time: str) -> str:
        """Calculate end time based on session duration"""
        start = datetime.strptime(start_time, '%H:%M:%S')
        end = start + timedelta(hours=Config.SESSION_DURATION_HOURS)
        return end.strftime('%H:%M:%S')