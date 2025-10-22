"""
OpenAI handler for managing the AI assistant and conversation flow.
"""

import logging
import json
from openai import OpenAI
from config import Config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class OpenAIHandler:
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.assistant_id = self._get_or_create_assistant()
    
    def _get_or_create_assistant(self):
        """Get existing assistant or create new one"""
        if Config.OPENAI_ASSISTANT_ID:
            return Config.OPENAI_ASSISTANT_ID
        
        # Create new assistant if not exists
        # Use gpt-4o-mini for assistant creation, gpt-4o-realtime-preview for actual calls
        assistant = self.client.beta.assistants.create(
            name=f"{Config.SPA_NAME} Booking Assistant",
            instructions=self._get_assistant_instructions(),
            model="gpt-4o-mini",  # Use compatible model for assistant creation
            tools=self._get_assistant_tools(),
            metadata={
                "spa_name": Config.SPA_NAME,
                "version": "1.0.0",
                "realtime_model": Config.OPENAI_MODEL  # Store the realtime model for actual calls
            }
        )
        
        logger.info(f"Created new assistant: {assistant.id}")
        return assistant.id
    
    def _get_assistant_instructions(self):
        """Get comprehensive instructions for the assistant"""
        slots_text = "\n".join([f"  - {slot['display']}" for slot in Config.TIME_SLOTS])
        
        return f"""You are a professional and friendly receptionist for {Config.SPA_NAME}, 
        a luxury spa in Italy. You handle phone bookings with Italian and English-speaking customers.

        IMPORTANT CONTEXT:
        - The caller's phone number is automatically provided: {{{{customer.phone}}}}
        - You don't need to ask for the phone number
        - Operating hours: 10:00 AM to 8:00 PM daily
        - Each session lasts {Config.SESSION_DURATION_HOURS} hours
        - Maximum capacity: {Config.MAX_CAPACITY_PER_SLOT} people per time slot
        
        AVAILABLE TIME SLOTS:
{slots_text}

        CONVERSATION FLOW:
        1. GREETING (Choose based on language):
           Italian: "Buongiorno, grazie per aver chiamato {Config.SPA_NAME}. Sono qui per aiutarla a prenotare una sessione spa rilassante."
           English: "Good day, thank you for calling {Config.SPA_NAME}. I'm here to help you book a relaxing spa session."

        2. CONFIRM PHONE NUMBER:
           "Vedo che sta chiamando dal numero {{{{customer.phone}}}}. È corretto per la prenotazione?"
           "I see you're calling from {{{{customer.phone}}}}. Is this correct for your booking?"

        3. COLLECT NAME:
           "Posso avere il suo nome, per favore?" / "May I have your name, please?"

        4. GET PREFERRED DATE:
           "Per quale data vorrebbe prenotare?" / "What date would you like to book?"
           - Accept various date formats
           - Confirm the understood date

        5. PRESENT AVAILABLE SLOTS:
           "Per [data], abbiamo disponibilità alle: [elenco slot]"
           "For [date], we have availability at: [list slots]"

        6. CHECK AND BOOK:
           - Use check_slot_availability to verify space
           - If available, use book_spa_slot to confirm
           - If full, suggest alternatives

        7. CONFIRMATION:
           "Perfetto! La sua sessione spa è confermata per [data] dalle [ora] alle [ora]. Il suo codice di prenotazione è [codice]."
           "Perfect! Your spa session is confirmed for [date] from [time] to [time]. Your booking reference is [code]."

        8. CLOSING:
           "Grazie per aver scelto {Config.SPA_NAME}. La aspettiamo!"
           "Thank you for choosing {Config.SPA_NAME}. We look forward to seeing you!"

        IMPORTANT BEHAVIORS:
        - Detect customer's language from their first response and continue in that language
        - Be patient and repeat information if needed
        - Handle dates intelligently (today, tomorrow, next Monday, etc.)
        - If slot is full, always offer alternatives
        - Always confirm details before finalizing
        - Speak clearly and at a moderate pace
        - Be empathetic and professional
        
        ERROR HANDLING:
        - If customer seems confused, offer to repeat or clarify
        - If technical issues occur, apologize and ask them to try again
        - Never reveal technical details about the system"""
    
    def _get_assistant_tools(self):
        """Define tools available to the assistant"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_slot_availability",
                    "description": "Check if a specific spa time slot has available space",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time in HH:MM format (e.g., 10:00, 14:00)"
                            }
                        },
                        "required": ["date", "start_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_spa_slot",
                    "description": "Book a spa session for a customer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Customer's full name"
                            },
                            "date": {
                                "type": "string",
                                "description": "Booking date in YYYY-MM-DD format"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Session start time in HH:MM format"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Session end time in HH:MM format"
                            }
                        },
                        "required": ["name", "date", "start_time", "end_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_latest_appointment",
                    "description": "Retrieve the most recent appointment for a customer by phone number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "Customer's phone number"
                            }
                        },
                        "required": ["phone_number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_appointment",
                    "description": "Cancel/delete a customer's appointment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "Customer's phone number"
                            },
                            "booking_reference": {
                                "type": "string",
                                "description": "Booking reference code (e.g., SPA-000123)"
                            }
                        },
                        "required": ["phone_number"]
                    }
                }
            }
        ]
    
    def create_thread(self, metadata=None):
        """Create a new conversation thread"""
        thread = self.client.beta.threads.create(metadata=metadata or {})
        return thread.id
    
    def send_message(self, thread_id, message):
        """Send a message to a thread"""
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
    
    def run_assistant(self, thread_id, additional_instructions=None):
        """Run the assistant on a thread"""
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
            additional_instructions=additional_instructions
        )
        return run