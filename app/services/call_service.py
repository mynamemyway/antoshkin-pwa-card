# app/services/call_service.py

"""
Flash Call verification service.

Handles Flash Call code generation and sending via SMS.ru API.
In Flash Call mode, the API generates the code and returns it in the response.

Functions:
- send_flash_call: Make a call to user's phone with verification code (async)
"""

import logging
from typing import Tuple

import httpx

from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Test code for development mode
TEST_CODE = "0000"  # Universal code for testing


async def send_flash_call(phone: str, ip: str) -> Tuple[bool, str, str]:
    """
    Send Flash Call with verification code via SMS.ru API.

    Args:
        phone: Normalized phone number (+7XXXXXXXXXX)
        ip: User's IP address (for anti-fraud protection)
            Use "-1" for manual sends or local IPs

    Returns:
        Tuple of (success: bool, code: str, message: str)
        - (True, "1435", "Call initiated") if successful
        - (False, "", "Error message") if failed

    Note:
        In test mode (SMS_TEST_MODE=True), returns stub response.
        In production, makes Flash Call via SMS.ru API using httpx.AsyncClient.

    SMS.ru API:
        GET https://sms.ru/code/call
        Params: api_id, phone, ip, partner_id (optional)

    Response format:
        {
            "status": "OK",
            "code": "1435",      # Last 4 digits of caller ID
            "call_id": "000000-10000000",
            "cost": 0.4,
            "balance": 4122.56
        }

    Usage:
        success, code, message = await send_flash_call("+79991234567", "192.168.1.1")
        if success:
            print(f"Call initiated, code: {code}")
    """
    # Test mode: return stub without making call
    if settings.SMS_TEST_MODE:
        logger.info(f"[CALL] Code {TEST_CODE} to {phone}")
        print(f"[CALL STUB] Code {TEST_CODE} will be sent to {phone}")
        return True, TEST_CODE, "Call initiated (test mode)"

    # Production mode: make Flash Call via SMS.ru API using httpx
    # Установлено значение "-1" вместо "ip", чтобы sms.ru не получал локальный ip
    url = "https://sms.ru/code/call"
    params = {
        "api_id": settings.SMS_API_KEY,
        "phone": phone,
        "ip": -1,
        "partner_id": "104935"  # Partner program ID
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            # Log full API response for debugging
            logger.debug(f"[CALL] SMS.ru response for {phone}: {data}")
            print(f"[CALL] SMS.ru response: {data}")

            if data.get("status") == "OK":
                code = data.get("code")
                call_id = data.get("call_id")
                cost = data.get("cost")
                balance = data.get("balance")

                logger.info(
                    f"[CALL] Initiated to {phone}, code: {code}, "
                    f"call_id: {call_id}, cost: {cost}, balance: {balance}"
                )
                return True, code, "Call initiated"
            else:
                error_msg = data.get("status_text", "Unknown error")
                status_code = data.get("status_code", "N/A")
                logger.error(
                    f"[CALL] SMS.ru error for {phone}: {error_msg} (code: {status_code})"
                )
                return False, "", f"SMS.ru error: {error_msg}"

    except httpx.TimeoutException as e:
        error_msg = "Request timeout"
        logger.error(f"[CALL] Timeout for {phone}: {error_msg}")
        return False, "", f"Network error: {error_msg}"

    except httpx.RequestError as e:
        error_msg = str(e)
        logger.error(f"[CALL] Request error for {phone}: {error_msg}")
        return False, "", f"Network error: {error_msg}"

    except ValueError as e:
        error_msg = "JSON parse error"
        logger.error(f"[CALL] JSON parse error for {phone}: {str(e)}")
        return False, "", f"Response error: {error_msg}"