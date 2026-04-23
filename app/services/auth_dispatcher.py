# app/services/auth_dispatcher.py

"""
Authorization dispatcher.

Selects the appropriate authorization method (SMS or Flash Call)
based on the AUTH_METHOD configuration setting.

Functions:
- send_verification_code: Send code via selected method (async)
- get_client_ip: Extract client IP from request (helper)
"""

import logging
from typing import Tuple, Optional

from fastapi import Request

from app.config import settings
from app.models import User
from app.services.sms_service import send_sms, generate_sms_code
from app.services.call_service import send_flash_call

# Configure logging
logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Handles X-Forwarded-For header for proxied requests.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address string, or "-1" if unavailable

    Note:
        Returns "-1" for local/manual sends as per SMS.ru documentation.
    """
    # Check for X-Forwarded-For header (proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Direct connection
    if request.client and request.client.host:
        return request.client.host

    # Fallback for local/manual sends
    return "-1"


async def send_verification_code(
    phone: str,
    request: Optional[Request] = None
) -> Tuple[bool, str, str]:
    """
    Send verification code using the configured method (SMS or Flash Call).

    Args:
        phone: Normalized phone number (+7XXXXXXXXXX)
        request: FastAPI request object (for IP extraction)

    Returns:
        Tuple of (success: bool, code: str, message: str)
        - Code is returned for storage in database
        - Message contains status or error description

    Logic:
        - If AUTH_METHOD = "sms": generate code locally, send via SMS
        - If AUTH_METHOD = "call": API generates code, returns it in response

    Usage:
        success, code, message = await send_verification_code(
            "+79991234567", request
        )
        if success:
            # Save code to database
            user.sms_code = code
    """
    # Get client IP for anti-fraud protection
    ip = get_client_ip(request) if request else "-1"

    if settings.AUTH_METHOD == "call":
        # Flash Call mode: API generates and returns the code
        logger.info(f"[DISPATCHER] Using Flash Call for {phone}")
        return await send_flash_call(phone, ip)
    else:
        # SMS mode (default): generate code locally and send via SMS
        logger.info(f"[DISPATCHER] Using SMS for {phone}")
        code = generate_sms_code()
        success, message = await send_sms(phone, code)
        return success, code, message