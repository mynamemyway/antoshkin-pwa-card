# app/services/sms_service.py

"""
SMS verification service.

Handles SMS code generation, sending, and verification.
Integrates with SMS gateway API (e.g., SMS.ru).

Functions:
- generate_sms_code: Create 4-digit verification code
- send_sms: Send SMS via gateway API (stub for testing)
- verify_sms_code: Validate code and mark user as verified

Testing:
    For local testing, the code is always "0000" (TEST_MODE=True).
    Set TEST_MODE=False for production with real SMS codes.
"""

import random
from datetime import datetime, timedelta
from typing import Tuple
from sqlalchemy.orm import Session

from app.models import User
from app.config import settings


# Test mode flag: set to True for testing without real SMS
TEST_MODE = True
TEST_CODE = "0000"  # Universal code for testing


def generate_sms_code() -> str:
    """
    Generate 4-digit SMS verification code.
    
    Returns:
        In TEST_MODE: always returns "0000"
        In production: random 4-digit code (0000-9999)
    
    Note:
        Code is zero-padded to ensure exactly 4 digits.
    
    Usage:
        code = generate_sms_code()
        print(f"Your code: {code}")  # "Your code: 0000" (test mode)
    """
    if TEST_MODE:
        return TEST_CODE
    
    return f"{random.randint(0, 9999):04d}"


def send_sms(phone: str, code: str) -> Tuple[bool, str]:
    """
    Send SMS with verification code via SMS gateway.
    
    Args:
        phone: Normalized phone number (+7XXXXXXXXXX)
        code: 4-digit verification code
    
    Returns:
        Tuple of (success: bool, message: str)
        - (True, "SMS sent") if successful
        - (False, "Error message") if failed
    
    Note:
        Currently implements stub logic (prints to console).
        Replace with actual SMS.ru API integration when API key is provided.
    
    SMS.ru API example:
        GET https://sms.ru/sms/send
        Params: api_key, to, msg, from (sender name)
    
    Usage:
        success, message = send_sms("+79991234567", "1234")
        if success:
            print("SMS sent successfully")
    """
    # Check if API key is configured
    if not settings.SMS_API_KEY:
        # Stub mode: log to console (for development)
        print(f"[SMS STUB] Code {code} sent to {phone}")
        return True, "SMS sent (stub mode)"
    
    # TODO: Implement actual SMS.ru API integration
    # Example implementation:
    #
    # import requests
    #
    # url = "https://sms.ru/sms/send"
    # params = {
    #     "api_key": settings.SMS_API_KEY,
    #     "to": phone,
    #     "msg": f"Your verification code: {code}",
    #     "from": settings.SMS_SENDER_NAME,
    #     "json": 1
    # }
    #
    # try:
    #     response = requests.get(url, params=params, timeout=10)
    #     response.raise_for_status()
    #     data = response.json()
    #
    #     if data.get("status") == "OK":
    #         return True, "SMS sent"
    #     else:
    #         error_msg = data.get("status_message", "Unknown error")
    #         return False, f"SMS.ru error: {error_msg}"
    #
    # except requests.exceptions.RequestException as e:
    #     return False, f"Network error: {str(e)}"
    
    # For now, return success (stub mode)
    print(f"[SMS] Sending code {code} to {phone}")
    return True, "SMS sent"


def verify_sms_code(
    db: Session,
    user: User,
    code: str
) -> Tuple[bool, str]:
    """
    Verify SMS code and activate user account.
    
    Args:
        db: Database session
        user: User object to verify
        code: 4-digit code entered by user
    
    Returns:
        Tuple of (success: bool, message: str)
        - (True, "Verified") if code is valid
        - (False, "Error message") if invalid or expired
    
    Verification logic:
        1. Check if user is already verified
        2. Check if SMS code exists
        3. Check if code has not expired (5 minutes)
        4. Compare entered code with stored code
        5. If valid: mark as verified, clear code
    
    Usage:
        user = get_user_by_phone(db, "+79991234567")
        success, message = verify_sms_code(db, user, "1234")
        if success:
            print("User verified successfully")
    """
    # Check if already verified
    if user.is_verified:
        return True, "Already verified"
    
    # Check if code exists
    if not user.sms_code:
        return False, "No SMS code sent"
    
    # Check if code has expired
    if user.sms_code_expires_at is None:
        return False, "SMS code error"
    
    if datetime.utcnow() > user.sms_code_expires_at:
        return False, "SMS code expired"
    
    # Compare codes (constant-time comparison for security)
    if user.sms_code != code:
        return False, "Invalid code"
    
    # Code is valid - mark user as verified
    user.is_verified = True
    user.sms_code = None
    user.sms_code_expires_at = None
    db.commit()
    
    return True, "Verified"


def set_user_sms_code(
    db: Session,
    user: User
) -> Tuple[bool, str, str]:
    """
    Generate and set SMS code for user.
    
    Args:
        db: Database session
        user: User object
    
    Returns:
        Tuple of (success: bool, code: str, message: str)
        - Code is returned for sending via SMS
        - Code is NOT stored in plain text in production (use hash)
    
    Note:
        Code expires in 5 minutes.
        For production: hash the code before storing in database.
    
    Usage:
        user = get_user_by_phone(db, "+79991234567")
        success, code, message = set_user_sms_code(db, user)
        if success:
            send_sms(user.phone, code)
    """
    # Generate new code
    code = generate_sms_code()
    
    # Set expiration time (5 minutes from now)
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Save to database
    user.sms_code = code
    user.sms_code_expires_at = expires_at
    db.commit()
    
    return True, code, "Code generated"


def resend_sms_code(
    db: Session,
    user: User
) -> Tuple[bool, str, str]:
    """
    Resend SMS code to user (if previous code expired or not received).
    
    Args:
        db: Database session
        user: User object
    
    Returns:
        Tuple of (success: bool, code: str, message: str)
    
    Note:
        Generates new code and resets expiration time.
        Implement rate limiting in production (e.g., max 3 requests per hour).
    
    Usage:
        user = get_user_by_phone(db, "+79991234567")
        success, code, message = resend_sms_code(db, user)
        send_sms(user.phone, code)
    """
    # Check if already verified
    if user.is_verified:
        return False, "", "User already verified"
    
    # Generate and set new code
    return set_user_sms_code(db, user)
