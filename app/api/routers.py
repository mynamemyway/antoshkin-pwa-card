# app/api/routers.py

"""
API routers for the loyalty card application.

Defines all HTTP endpoints for:
- User registration and verification
- SMS code sending and validation
- Session management (login, logout, me)
- Card display
- Admin panel and data export
"""

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

from app.database import get_db, get_async_db
from app.models import User, Session
from app.config import settings
from app.schemas import (
    UserCreate,
    UserOut,
    UserVerify,
    UserListOut,
    SMSRequest,
    SMSResponse,
    VerifyResponse,
)
from app.services.crud import (
    get_user_by_phone,
    create_user,
)
from app.services.auth_dispatcher import send_verification_code
from app.services.sms_service import verify_sms_code
from app.services.check_call_service import verify_check_call_status
from app.services.session_service import (
    create_session,
    get_session_by_token,
    delete_session,
)

# Create router instance
router = APIRouter()

# Cookie configuration
COOKIE_NAME = "session_token"
COOKIE_MAX_AGE = 2592000  # 30 days in seconds
COOKIE_PATH = "/"

# ============== Page Routes (GET) ==============

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Root endpoint - serves the main registration page.

    Args:
        request: FastAPI request object (required for templates)

    Returns:
        Rendered HTML template for the registration page
    """
    return request.state.templates.TemplateResponse("index.html", {"request": request})


@router.get("/splash", response_class=HTMLResponse)
async def splash_page(request: Request):
    """
    Splash screen for PWA - displayed when app is launched from home screen.

    Args:
        request: FastAPI request object (required for templates)

    Returns:
        Rendered splash screen HTML template
    """
    return request.state.templates.TemplateResponse("splash.html", {"request": request})


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request):
    """
    Verification page - SMS code input.

    Args:
        request: FastAPI request object (required for templates)

    Returns:
        Rendered HTML template for the verification page
    """
    from app.config import settings
    return request.state.templates.TemplateResponse("verify.html", {
        "request": request,
        "auth_method": settings.AUTH_METHOD
    })


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50
):
    """
    Admin panel - displays list of all users with pagination and search.

    Args:
        request: FastAPI request object
        db: AsyncSession database session
        search: Optional phone number search query (filters entire database)
        page: Page number for pagination (default: 1)
        per_page: Number of users per page (default: 50)

    Returns:
        Rendered admin panel HTML template
    """
    # Ensure page is at least 1
    page = max(1, page)

    # Build base query with search filter
    stmt = select(User)
    if search:
        stmt = stmt.where(User.phone.ilike(f"%{search}%"))

    # Get total count (before pagination)
    count_stmt = select(func.count()).select_from(User)
    if search:
        count_stmt = count_stmt.where(User.phone.ilike(f"%{search}%"))

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Calculate offset and total pages
    offset = (page - 1) * per_page
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    # Get users for current page (ordered by created_at desc)
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    users = result.scalars().all()

    # Get verified count (from entire database, not just filtered)
    verified_stmt = select(func.count()).select_from(User).where(User.is_verified == True)
    verified_result = await db.execute(verified_stmt)
    verified_count = verified_result.scalar() or 0

    return request.state.templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "users": users,
            "total": total,
            "verified_count": verified_count,
            "search": search or "",
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "offset": offset
        }
    )


@router.get("/admin/export")
async def export_users(request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Export all users to CSV file.

    Args:
        request: FastAPI request object
        db: AsyncSession database session

    Returns:
        CSV file with user data for download
    """
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['id', 'full_name', 'phone', 'is_verified', 'created_at'])

    # Write user data
    for user in users:
        writer.writerow([
            user.id,
            user.full_name,
            user.phone,
            user.is_verified,
            user.created_at.isoformat()
        ])

    # Create response with CSV file
    csv_content = output.getvalue()
    output.close()

    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )


@router.get("/card/{phone}", response_class=HTMLResponse)
async def card_page(request: Request, phone: str, db: AsyncSession = Depends(get_async_db)):
    """
    Display user's loyalty card with QR code.

    Args:
        request: FastAPI request object
        phone: Normalized phone number
        db: AsyncSession database session

    Returns:
        Rendered card HTML template (only for verified users)
    """
    user = await get_user_by_phone(db, phone)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_verified:
        # Redirect to verification page if not verified
        return request.state.templates.TemplateResponse(
            "verify.html",
            {"request": request, "phone": phone}
        )

    return request.state.templates.TemplateResponse(
        "card.html",
        {"request": request, "user": user}
    )


# ============== API Routes (POST) ==============

@router.post("/api/register", response_model=UserOut)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Register new user or return existing user data.

    Args:
        user_data: User registration data (full_name, phone)
        db: AsyncSession database session

    Returns:
        User data (existing or newly created)

    Raises:
        HTTPException: If phone number format is invalid
    """
    # Check if user already exists
    existing_user = await get_user_by_phone(db, user_data.phone)

    if existing_user:
        # Return existing user data
        return existing_user

    # Create new user with race condition handling
    try:
        new_user = await create_user(db, user_data.full_name, user_data.phone)
        return new_user
    except IntegrityError:
        # Race condition: another request created the user
        await db.rollback()
        # Fetch and return the existing user
        existing_user = await get_user_by_phone(db, user_data.phone)
        if existing_user:
            return existing_user
        # Should not happen, but raise if user still not found
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.post("/api/send-sms", response_model=SMSResponse)
async def send_sms_endpoint(sms_data: SMSRequest, request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Send verification code to user (SMS, Flash Call, or Check Call).

    Args:
        sms_data: Phone number for verification
        request: FastAPI request object (for IP extraction)
        db: AsyncSession database session

    Returns:
        {"sent": true} if verification was initiated successfully

    Raises:
        HTTPException: If user not found or verification initiation failed

    Note:
        For check_call method: saves check_id to sms_check_id field
        For SMS/Flash Call: saves code to sms_code field
    """
    user = await get_user_by_phone(db, sms_data.phone)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Send code via configured method (SMS, Flash Call, or Check Call)
    success, code, message = await send_verification_code(user.phone, request)

    if not success:
        raise HTTPException(status_code=500, detail=message)

    # Save verification data to database based on auth method
    if settings.AUTH_METHOD == "check_call":
        # Check Call mode: save check_id for webhook verification
        user.sms_check_id = code
        user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        logger.info(f"[API] Check call initiated for {user.phone}, check_id: {code}")
    else:
        # SMS/Flash Call mode: save code for manual verification
        user.sms_code = code
        user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)

    await db.commit()

    return SMSResponse(sent=True)


@router.post("/api/verify", response_model=VerifyResponse)
async def verify_code(
    verify_data: UserVerify,
    db: AsyncSession = Depends(get_async_db),
    response: Response = None
):
    """
    Verify SMS code and activate user account.

    Args:
        verify_data: Phone number and verification code
        db: AsyncSession database session
        response: FastAPI response object (for setting cookie)

    Returns:
        {"verified": true} if code is valid

    Raises:
        HTTPException: If user not found, code invalid, or expired

    Note:
        All users must enter SMS code for verification, including previously verified users.
        This ensures security when logging in after logout.
    """
    user = await get_user_by_phone(db, verify_data.phone)

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Verify SMS code using service function
    success, message = await verify_sms_code(db, user, verify_data.code)

    if not success:
        # Map service messages to HTTP status codes
        if "Код не был отправлен" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "истёк" in message.lower() or "ошибка" in message.lower():
            raise HTTPException(status_code=400, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)

    # Save user_id BEFORE commit (user becomes expired after commit in async)
    user_id = user.id

    # Create session and set cookie
    token = await create_session(db, user_id)

    # Set HttpOnly cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        path=COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return VerifyResponse(verified=True)

# ============== Session API Routes ==============

@router.post("/api/login")
async def login(
    sms_data: SMSRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    response: Response = None
):
    """
    Login by phone number.

    Logic:
    - Check if phone exists in database
    - If found (any status): send SMS code, return 200 OK (redirect to verify)
    - If not found: return 404 Not Found (frontend should trigger registration)

    Args:
        sms_data: Phone number for login
        request: FastAPI request object (for IP extraction)
        db: AsyncSession database session
        response: FastAPI response object

    Returns:
        {"sent": true} if SMS was sent successfully

    Raises:
        HTTPException: 404 if user not found (trigger registration)

    Usage (Frontend):
        # Try to login
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({phone: '+79991234567'})
        });

        if (response.status === 404) {
            // User not found - start registration flow
        } else if (response.ok) {
            // SMS sent - redirect to verification page
        }
    """
    # Find user by phone
    user = await get_user_by_phone(db, sms_data.phone)

    if not user:
        # User not found - frontend should trigger registration
        raise HTTPException(status_code=404, detail="User not found")

    # User exists - send code via configured method (SMS or Flash Call)
    # This handles Scenario 3 (verified, no cookie) and Scenario 4 (not verified)

    # Send code via configured method
    success, code, message = await send_verification_code(user.phone, request)

    if not success:
        raise HTTPException(status_code=500, detail=message)

    # Code sent successfully - save to database based on auth method
    if settings.AUTH_METHOD == "check_call":
        # Check Call mode: save check_id for webhook verification
        user.sms_check_id = code
        user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        logger.info(f"[API] Check call initiated for {user.phone}, check_id: {code}")
    else:
        # SMS/Flash Call mode: save code for manual verification
        user.sms_code = code
        user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)

    await db.commit()

    return SMSResponse(sent=True)


# ============== Check Call Webhook ==============

@router.post("/api/auth/webhook/sms-ru")
async def sms_ru_webhook(request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Webhook endpoint for SMS.ru Check Call notifications.

    Receives automatic notifications from SMS.ru when a user completes a check call.
    Updates user verification status based on webhook data.

    Expected POST data from SMS.ru:
        - check_id: Verification ID
        - status: Call status (401 = verified)
        - phone: User's phone number (optional, for logging)

    Response format from SMS.ru:
        {
            "check_id": "201737-542",
            "status": "401",  // 401 = verified, 400 = pending, 402 = expired
            "phone": "79991234567"
        }

    Args:
        request: FastAPI request object (for form data)
        db: AsyncSession database session

    Returns:
        {"status": "OK"} if webhook processed successfully

    Note:
        SMS.ru sends this webhook when user completes the check call.
        Server marks user as verified and clears sms_check_id.
    """
    try:
        # Parse form data from SMS.ru
        form_data = await request.form()
        check_id = form_data.get("check_id")
        status = form_data.get("status")
        phone = form_data.get("phone", "unknown")

        logger.info(f"[WEBHOOK] Received from SMS.ru: check_id={check_id}, status={status}, phone={phone}")

        if not check_id or not status:
            logger.warning(f"[WEBHOOK] Missing check_id or status in webhook")
            return {"status": "error", "message": "Missing required fields"}

        # Check if status indicates successful verification (401 = verified)
        if status == "401":
            # Find user by check_id
            from sqlalchemy import select
            stmt = select(User).where(User.sms_check_id == check_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                # Mark user as verified
                user.is_verified = True
                user.sms_check_id = None  # Clear check_id after successful verification
                user.sms_code = None
                user.sms_code_expires_at = None
                await db.commit()

                logger.info(f"[WEBHOOK] User {user.phone} verified via check call")
                return {"status": "OK"}
            else:
                logger.warning(f"[WEBHOOK] User not found for check_id: {check_id}")
                return {"status": "error", "message": "User not found"}
        else:
            logger.info(f"[WEBHOOK] Check call status {status} for check_id: {check_id}")
            return {"status": "OK", "message": f"Status: {status}"}

    except Exception as e:
        logger.error(f"[WEBHOOK] Error processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.get("/api/auth/check-call-status")
async def check_call_status(
    phone: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Check verification status for Check Call method (polling endpoint).

    Frontend polls this endpoint every 2-3 seconds to detect when
    the webhook has updated the user's verification status.

    Args:
        phone: Normalized phone number (+7XXXXXXXXXX)
        db: AsyncSession database session

    Returns:
        {
            "verified": bool,
            "status": str  # "pending", "verified", "expired"
        }

    Usage (Frontend):
        const response = await fetch('/api/auth/check-call-status?phone=+79991234567');
        const data = await response.json();
        if (data.verified) {
            // Redirect to card page
        }
    """
    user = await get_user_by_phone(db, phone)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is verified
    if user.is_verified:
        return {"verified": True, "status": "verified"}

    # Check if check_id exists and not expired
    if user.sms_check_id and user.sms_code_expires_at:
        if datetime.utcnow() > user.sms_code_expires_at:
            return {"verified": False, "status": "expired"}
        return {"verified": False, "status": "pending"}

    # No active check call
    return {"verified": False, "status": "none"}


# ============== Session API Routes ==============

@router.post("/api/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Logout user (delete session).

    Logic:
    - Get session token from cookie
    - Delete session from database
    - Clear cookie in browser

    Args:
        request: FastAPI request object (for cookie access)
        db: AsyncSession database session

    Returns:
        {"success": true} if logged out successfully
    """
    # Get token from cookie
    token = request.cookies.get(COOKIE_NAME)

    if token:
        # Delete session from database
        await delete_session(db, token)

    # Create response with cookie cleared
    response = Response(content='{"success": true}')
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return response


@router.get("/api/me", response_model=UserOut)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get current authenticated user.

    Logic:
    - Middleware already validated session and set request.state.current_user
    - Just return the user if authenticated

    Args:
        request: FastAPI request object (for cookie access)
        db: AsyncSession database session

    Returns:
        User data if authenticated

    Raises:
        HTTPException: 401 Unauthorized if not authenticated

    Usage (Frontend):
        # Check if user is authenticated
        const response = await fetch('/api/me', {
            credentials: 'include'  // Send cookies automatically
        });

        if (response.ok) {
            const user = await response.json();
            // User is authenticated
        } else if (response.status === 401) {
            // Not authenticated - show login form
        }
    """
    # Get user from request.state (injected by middleware)
    user = request.state.current_user

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Return user data
    return user