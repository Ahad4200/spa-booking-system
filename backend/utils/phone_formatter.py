"""
Phone number formatting utilities for Italian and international numbers.
Handles various phone number formats and validates them.
"""

import re
from typing import Optional, Tuple

class PhoneFormatter:
    """Handles phone number formatting and validation"""
    
    # Italian phone number patterns
    ITALIAN_MOBILE_PATTERN = r'^3\d{8,9}$'
    ITALIAN_LANDLINE_PATTERN = r'^0\d{8,10}$'
    
    # Country codes
    COUNTRY_CODES = {
        'IT': '+39',
        'US': '+1',
        'UK': '+44',
        'FR': '+33',
        'DE': '+49',
        'ES': '+34',
        'CH': '+41'
    }
    
    @staticmethod
    def clean_number(phone_number: str) -> str:
        """Remove all non-numeric characters from phone number"""
        return re.sub(r'\D', '', phone_number)
    
    @staticmethod
    def format_italian_number(phone_number: str) -> str:
        """
        Format Italian phone numbers to standard format.
        
        Examples:
        - 3331234567 -> +39 333 123 4567
        - 0612345678 -> +39 06 1234 5678
        - +393331234567 -> +39 333 123 4567
        """
        # Clean the number
        cleaned = PhoneFormatter.clean_number(phone_number)
        
        # Remove country code if present
        if cleaned.startswith('39'):
            cleaned = cleaned[2:]
        elif cleaned.startswith('00139'):
            cleaned = cleaned[5:]
        
        # Check if it's a mobile number (starts with 3)
        if cleaned.startswith('3'):
            # Format: +39 3XX XXX XXXX
            if len(cleaned) == 9:
                return f"+39 {cleaned[:3]} {cleaned[3:6]} {cleaned[6:]}"
            elif len(cleaned) == 10:
                return f"+39 {cleaned[:3]} {cleaned[3:6]} {cleaned[6:]}"
        
        # Check if it's a landline (starts with 0)
        elif cleaned.startswith('0'):
            # Rome/Milan format (02, 06)
            if cleaned[:2] in ['02', '06']:
                # Format: +39 0X XXXX XXXX
                return f"+39 {cleaned[:2]} {cleaned[2:6]} {cleaned[6:]}"
            # Other cities (3-digit prefix)
            else:
                # Format: +39 0XX XXXX XXX
                return f"+39 {cleaned[:3]} {cleaned[3:7]} {cleaned[7:]}"
        
        # If no special formatting applies, just add country code
        return f"+39 {cleaned}"
    
    @staticmethod
    def format_international(phone_number: str, country_code: str = 'IT') -> str:
        """
        Format international phone numbers.
        
        Args:
            phone_number: The phone number to format
            country_code: ISO country code (default: IT)
        
        Returns:
            Formatted phone number with country code
        """
        cleaned = PhoneFormatter.clean_number(phone_number)
        
        # Get country prefix
        prefix = PhoneFormatter.COUNTRY_CODES.get(country_code, '+39')
        
        # Remove country code if already present
        prefix_digits = prefix[1:]
        if cleaned.startswith(prefix_digits):
            cleaned = cleaned[len(prefix_digits):]
        
        # Special formatting for Italy
        if country_code == 'IT':
            return PhoneFormatter.format_italian_number(cleaned)
        
        # Generic international format
        return f"{prefix} {cleaned}"
    
    @staticmethod
    def validate_italian_number(phone_number: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Italian phone number.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        cleaned = PhoneFormatter.clean_number(phone_number)
        
        # Remove country code if present
        if cleaned.startswith('39'):
            cleaned = cleaned[2:]
        
        # Check mobile numbers
        if cleaned.startswith('3'):
            if re.match(PhoneFormatter.ITALIAN_MOBILE_PATTERN, cleaned):
                return True, None
            else:
                return False, "Invalid Italian mobile number format"
        
        # Check landline numbers
        elif cleaned.startswith('0'):
            if re.match(PhoneFormatter.ITALIAN_LANDLINE_PATTERN, cleaned):
                return True, None
            else:
                return False, "Invalid Italian landline number format"
        
        return False, "Phone number must start with 3 (mobile) or 0 (landline)"
    
    @staticmethod
    def extract_from_twilio(twilio_number: str) -> str:
        """
        Extract and format number from Twilio format.
        
        Twilio provides numbers like: +393331234567
        We want to store them as: +39 333 123 4567
        """
        if not twilio_number:
            return ""
        
        # Twilio already provides in E.164 format
        if twilio_number.startswith('+'):
            # Determine country and format accordingly
            if twilio_number.startswith('+39'):
                # Italian number
                return PhoneFormatter.format_italian_number(twilio_number)
            else:
                # Other international number
                return twilio_number
        
        # Fallback to basic formatting
        return PhoneFormatter.format_italian_number(twilio_number)
    
    @staticmethod
    def to_e164(phone_number: str, default_country: str = 'IT') -> str:
        """
        Convert phone number to E.164 format for Twilio.
        
        E.164 format: +[country code][number] with no spaces or special characters
        Example: +393331234567
        """
        cleaned = PhoneFormatter.clean_number(phone_number)
        
        # Add country code if not present
        if not cleaned.startswith('39') and default_country == 'IT':
            # Check if it's a valid Italian number format
            if cleaned.startswith('3') or cleaned.startswith('0'):
                cleaned = '39' + cleaned
        
        # Ensure it starts with +
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        
        return cleaned
    
    @staticmethod
    def mask_for_privacy(phone_number: str) -> str:
        """
        Mask phone number for privacy (show only last 4 digits).
        
        Example: +39 333 123 4567 -> +39 *** *** 4567
        """
        # Clean and format first
        formatted = PhoneFormatter.format_italian_number(phone_number)
        
        # Split by spaces
        parts = formatted.split(' ')
        
        if len(parts) >= 3:
            # Keep country code and last part, mask the middle
            masked_parts = [parts[0]]  # Country code
            for i in range(1, len(parts) - 1):
                masked_parts.append('***')
            masked_parts.append(parts[-1])  # Last 4 digits
            return ' '.join(masked_parts)
        
        # Fallback: just mask the middle part
        if len(formatted) > 8:
            return formatted[:5] + '****' + formatted[-4:]
        
        return formatted
    
    @staticmethod
    def get_number_type(phone_number: str) -> str:
        """
        Determine if number is mobile or landline.
        
        Returns:
            'mobile', 'landline', or 'unknown'
        """
        cleaned = PhoneFormatter.clean_number(phone_number)
        
        # Remove country code if present
        if cleaned.startswith('39'):
            cleaned = cleaned[2:]
        
        if cleaned.startswith('3'):
            return 'mobile'
        elif cleaned.startswith('0'):
            return 'landline'
        
        return 'unknown'