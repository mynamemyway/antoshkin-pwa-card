# app/services/check_call_service.py

"""
Check Call verification service.

Handles Check Call authorization flow via SMS.ru API.
In Check Call mode, the user makes a call to a specified number for verification.

Functions:
- initiate_check_call: Request a check call from SMS.ru (async)
- verify_check_call_status: Check verification status via API (async, optional polling)
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User

# Configure logging
logger = logging.getLogger(__name__)


async def initiate_check_call(
    db: AsyncSession,
    user: User,
    phone: str
) -> Tuple[bool, str, str]:
    """
    Initiate Check Call verification via SMS.ru API.

    Args:
        db: AsyncSession database session
        user: User object to update
        phone: Normalized phone number (+7XXXXXXXXXX)

    Returns:
        Tuple of (success: bool, check_id: str, message: str)
        - check_id: Verification ID (or TEST stub in test mode)
        - message: Status or error description

    Note:
        In test mode (SMS_TEST_MODE=True):
        - Returns stub response
        - Immediately marks user as verified (is_verified=True)
        - Clears temporary fields (sms_check_id, sms_code_expires_at)

        In production:
        - Makes request to SMS.ru /callcheck/add endpoint
        - Saves check_id to user.sms_check_id for webhook verification

    SMS.ru API:
        GET https://sms.ru/callcheck/add
        Params: api_id, phone, json

    Response format:
        {
            "status": "OK",
            "status_code": 100,
            "check_id": "201737-542",
            "call_phone": "78005008275",
            "call_phone_pretty": "+7 (800) 500-8275",
            "call_phone_html": "<a href=\"callto:78005008275\">+7 (800) 500-8275</a>"
        }

    Usage:
        success, check_id, message = await initiate_check_call(db, user, "+79991234567")
        if success:
            await db.commit()  # User already updated in service
    """
    from datetime import timedelta

    # Test mode: make REAL request to SMS.ru but auto-verify immediately
    if settings.SMS_TEST_MODE:
        logger.info(f"[CHECK_CALL] Initiated for {phone} (test mode with real API)")

        # Make real request to get actual check_id
        url = "https://sms.ru/callcheck/add"
        params = {
            "api_id": settings.SMS_API_KEY,
            "phone": phone.lstrip('+'),
            "json": 1
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "OK":
                    real_check_id = data.get("check_id")
                    logger.info(f"[CHECK_CALL] Got real check_id {real_check_id} in test mode")
                    print(f"[CHECK_CALL] SMS.ru response (test mode): {data}")

                    # Save real check_id temporarily
                    user.sms_check_id = real_check_id
                    user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
                    await db.commit()

                    # Immediately mark as verified (emulating webhook)
                    user.is_verified = True
                    user.sms_check_id = None
                    user.sms_code_expires_at = None
                    await db.commit()

                    logger.info(f"[CHECK_CALL] Test mode: User {user.phone} auto-verified with real check_id")
                    return True, real_check_id, "Check call initiated (test mode)"
                else:
                    error_msg = data.get("status_text", "Unknown error")
                    logger.error(f"[CHECK_CALL] SMS.ru error in test mode: {error_msg}")
                    return False, "", f"SMS.ru error: {error_msg}"
        except Exception as e:
            logger.error(f"[CHECK_CALL] Request error in test mode: {str(e)}")
            return False, "", f"Network error: {str(e)}"

    # Production mode: request check call via SMS.ru API using httpx
    url = "https://sms.ru/callcheck/add"
    params = {
        "api_id": settings.SMS_API_KEY,
        "phone": phone.lstrip('+'),  # Remove + prefix for API
        "json": 1
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            # Log full API response for debugging
            logger.debug(f"[CHECK_CALL] SMS.ru response for {phone}: {data}")
            print(f"[CHECK_CALL] SMS.ru response: {data}")

            if data.get("status") == "OK":
                check_id = data.get("check_id")
                call_phone = data.get("call_phone")
                call_phone_pretty = data.get("call_phone_pretty", call_phone)

                # Update user with check_id for webhook verification
                user.sms_check_id = check_id
                user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)

                logger.info(
                    f"[CHECK_CALL] Initiated for {phone}, "
                    f"check_id: {check_id}, call_phone: {call_phone_pretty}"
                )
                return True, check_id, "Check call initiated"
            else:
                error_msg = data.get("status_text", "Unknown error")
                status_code = data.get("status_code", "N/A")
                logger.error(
                    f"[CHECK_CALL] SMS.ru error for {phone}: {error_msg} (code: {status_code})"
                )
                return False, "", f"SMS.ru error: {error_msg}"

    except httpx.TimeoutException as e:
        error_msg = "Request timeout"
        logger.error(f"[CHECK_CALL] Timeout for {phone}: {error_msg}")
        return False, "", f"Network error: {error_msg}"

    except httpx.RequestError as e:
        error_msg = str(e)
        logger.error(f"[CHECK_CALL] Request error for {phone}: {error_msg}")
        return False, "", f"Network error: {error_msg}"

    except ValueError as e:
        error_msg = "JSON parse error"
        logger.error(f"[CHECK_CALL] JSON parse error for {phone}: {str(e)}")
        return False, "", f"Response error: {error_msg}"


async def verify_check_call_status(check_id: str) -> Tuple[bool, str, str]:
    """
    Verify Check Call status via SMS.ru API (optional polling method).

    This is an alternative to webhook-based verification.
    Can be used for manual status checks or fallback polling.

    Args:
        check_id: Verification ID from initiate_check_call

    Returns:
        Tuple of (success: bool, status: str, message: str)
        - status: "401" (verified), "400" (pending), "402" (expired/invalid)
        - message: Text description of status

    SMS.ru API:
        GET https://sms.ru/callcheck/status
        Params: api_id, check_id, json

    Response format:
        {
            "status": "OK",
            "status_code": 100,
            "check_status": "401",
            "check_status_text": "Авторизация по звонку: номер подтвержден"
        }

    Status codes:
        - 100: Request successful, waiting for call
        - 400: Not verified yet (no call received)
        - 401: Verified (call received)
        - 402: Expired or invalid check_id

    Usage:
        success, status, message = await verify_check_call_status("201737-542")
        if success and status == "401":
            # User is verified
    """
    # Test mode: return stub
    if settings.SMS_TEST_MODE:
        logger.info(f"[CHECK_CALL] Status check for {check_id} (test mode)")
        # Simulate verified status for test IDs
        if check_id.startswith("TEST-"):
            return True, "401", "Авторизация по звонку: номер подтвержден (test)"
        return True, "400", "Ожидание звонка (test)"

    # Production mode: check status via SMS.ru API
    url = "https://sms.ru/callcheck/status"
    params = {
        "api_id": settings.SMS_API_KEY,
        "check_id": check_id,
        "json": 1
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            # Log full API response for debugging
            logger.debug(f"[CHECK_CALL] Status response for {check_id}: {data}")
            print(f"[CHECK_CALL] Status response: {data}")

            if data.get("status") == "OK":
                check_status = data.get("check_status")
                check_status_text = data.get("check_status_text", "Unknown status")

                logger.info(
                    f"[CHECK_CALL] Status for {check_id}: {check_status} - {check_status_text}"
                )
                return True, check_status, check_status_text
            else:
                error_msg = data.get("status_text", "Unknown error")
                status_code = data.get("status_code", "N/A")
                logger.error(
                    f"[CHECK_CALL] SMS.ru status error for {check_id}: {error_msg} (code: {status_code})"
                )
                return False, "", f"SMS.ru error: {error_msg}"

    except httpx.TimeoutException as e:
        error_msg = "Request timeout"
        logger.error(f"[CHECK_CALL] Timeout for {check_id}: {error_msg}")
        return False, "", f"Network error: {error_msg}"

    except httpx.RequestError as e:
        error_msg = str(e)
        logger.error(f"[CHECK_CALL] Request error for {check_id}: {error_msg}")
        return False, "", f"Network error: {error_msg}"

    except ValueError as e:
        error_msg = "JSON parse error"
        logger.error(f"[CHECK_CALL] JSON parse error for {check_id}: {str(e)}")
        return False, "", f"Response error: {error_msg}"