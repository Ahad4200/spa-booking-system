"""
Supabase handler for database operations.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional
from supabase import create_client, Client
from config import Config

logger = logging.getLogger(__name__)

class SupabaseHandler:
    def __init__(self):
        self.client: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_KEY
        )
    
    def create_call_session(self, session_data: Dict) -> str:
        """Create a new call session record"""
        try:
            response = self.client.table('call_sessions').insert(session_data).execute()
            return response.data[0]['id']
        except Exception as e:
            logger.error(f"Failed to create call session: {str(e)}")
            raise
    
    def update_call_session(self, call_sid: str, updates: Dict) -> bool:
        """Update an existing call session"""
        try:
            self.client.table('call_sessions')\
                .update(updates)\
                .eq('call_id', call_sid)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update call session: {str(e)}")
            return False
    
    def check_slot_availability(self, booking_date: str, start_time: str) -> Dict:
        """Check if a slot has available space"""
        try:
            # Format time properly
            if len(start_time) == 5:  # HH:MM format
                start_time += ':00'
            
            # Call RPC function
            response = self.client.rpc(
                'check_slot_availability',
                {
                    'p_date': booking_date,
                    'p_start_time': start_time
                }
            ).execute()
            
            result = response.data
            
            # Format response for OpenAI
            if result.get('status') == 'success':
                return {
                    'available': True,
                    'spots_remaining': result.get('spots_remaining', 0),
                    'message': f"Slot available with {result.get('spots_remaining')} spots remaining"
                }
            else:
                return {
                    'available': False,
                    'message': result.get('message', 'Slot is full')
                }
                
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def book_spa_slot(self, booking_data: Dict) -> Dict:
        """Create a spa booking"""
        try:
            # Format times
            start_time = booking_data['start_time']
            end_time = booking_data['end_time']
            
            if len(start_time) == 5:
                start_time += ':00'
            if len(end_time) == 5:
                end_time += ':00'
            
            # Call RPC function
            response = self.client.rpc(
                'book_spa_slot',
                {
                    'p_customer_name': booking_data.get('name') or booking_data.get('customer_name'),
                    'p_customer_phone': booking_data.get('phone') or booking_data.get('customer_phone'),
                    'p_booking_date': booking_data.get('date') or booking_data.get('booking_date'),
                    'p_slot_start_time': start_time,
                    'p_slot_end_time': end_time
                }
            ).execute()
            
            result = response.data
            
            if result.get('status') == 'success':
                return {
                    'success': True,
                    'booking_id': result.get('booking_id'),
                    'reference': result.get('booking_reference'),
                    'message': result.get('message'),
                    'details': {
                        'date': booking_data['date'],
                        'time': f"{booking_data['start_time']} - {booking_data['end_time']}",
                        'name': booking_data['name']
                    }
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Booking failed')
                }
                
        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_bookings_for_date(self, booking_date: str) -> List[Dict]:
        """Get all bookings for a specific date"""
        try:
            response = self.client.table('spa_bookings')\
                .select('*')\
                .eq('booking_date', booking_date)\
                .order('slot_start_time')\
                .execute()
            
            return response.data
        except Exception as e:
            logger.error(f"Error fetching bookings: {str(e)}")
            return []
    
    def cancel_booking(self, booking_id: int) -> bool:
        """Cancel a booking"""
        try:
            self.client.table('spa_bookings')\
                .delete()\
                .eq('id', booking_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Error canceling booking: {str(e)}")
            return False