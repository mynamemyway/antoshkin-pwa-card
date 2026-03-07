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
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Session
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
from app.services.sms_service import (
    generate_sms_code,
    send_sms,
    verify_sms_code,
    set_user_sms_code,
)
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
    return request.state.templates.TemplateResponse("verify.html", {"request": request})


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50
):
    """
    Admin panel - displays list of all users with pagination and search.

    Args:
        request: FastAPI request object
        db: Database session
        search: Optional phone number search query (filters entire database)
        page: Page number for pagination (default: 1)
        per_page: Number of users per page (default: 50)

    Returns:
        Rendered admin panel HTML template
    """
    # Ensure page is at least 1
    page = max(1, page)
    
    # Build base query
    query = db.query(User)
    
    # Apply search filter if provided
    if search:
        query = query.filter(User.phone.ilike(f"%{search}%"))
    
    # Get total count (before pagination)
    total = query.count()
    
    # Calculate offset and total pages
    offset = (page - 1) * per_page
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Get users for current page (ordered by created_at desc)
    users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Get verified count (from entire database, not just filtered)
    verified_count = db.query(User).filter(User.is_verified == True).count()
    
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
async def export_users(request: Request, db: Session = Depends(get_db)):
    """
    Export all users to CSV file.
    
    Args:
        request: FastAPI request object
        db: Database session
    
    Returns:
        CSV file with user data for download
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    
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
async def card_page(request: Request, phone: str, db: Session = Depends(get_db)):
    """
    Display user's loyalty card with QR code.
    
    Args:
        request: FastAPI request object
        phone: Normalized phone number
        db: Database session
    
    Returns:
        Rendered card HTML template (only for verified users)
    """
    user = get_user_by_phone(db, phone)
    
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
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register new user or return existing user data.
    
    Args:
        user_data: User registration data (full_name, phone)
        db: Database session
    
    Returns:
        User data (existing or newly created)
    
    Raises:
        HTTPException: If phone number format is invalid
    """
    # Check if user already exists
    existing_user = get_user_by_phone(db, user_data.phone)
    
    if existing_user:
        # Return existing user data
        return existing_user
    
    # Create new user
    new_user = create_user(db, user_data.full_name, user_data.phone)
    return new_user


@router.post("/api/send-sms", response_model=SMSResponse)
async def send_sms_code(sms_data: SMSRequest, db: Session = Depends(get_db)):
    """
    Send SMS verification code to user.
    
    Args:
        sms_data: Phone number for SMS delivery
        db: Database session
    
    Returns:
        {"sent": true} if SMS was sent successfully
    
    Raises:
        HTTPException: If user not found
    """
    user = get_user_by_phone(db, sms_data.phone)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate and save code (for ALL users, including verified)
    # Verified users need SMS code for re-login after logout
    code = generate_sms_code()
    user.sms_code = code
    user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
    db.commit()

    # Send SMS
    sms_sent = send_sms(user.phone, code)

    if not sms_sent:
        raise HTTPException(status_code=500, detail="Failed to send SMS")

    return SMSResponse(sent=True)


@router.post("/api/verify", response_model=VerifyResponse)
async def verify_code(
    verify_data: UserVerify,
    db: Session = Depends(get_db),
    response: Response = None
):
    """
    Verify SMS code and activate user account.

    Args:
        verify_data: Phone number and verification code
        db: Database session
        response: FastAPI response object (for setting cookie)

    Returns:
        {"verified": true} if code is valid

    Raises:
        HTTPException: If user not found, code invalid, or expired

    Note:
        All users must enter SMS code for verification, including previously verified users.
        This ensures security when logging in after logout.
    """
    user = get_user_by_phone(db, verify_data.phone)

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Check if code exists (required for all users, including verified)
    if not user.sms_code:
        raise HTTPException(status_code=400, detail="Код не был отправлен")

    # Check if code has expired
    if user.sms_code_expires_at is None or datetime.utcnow() > user.sms_code_expires_at:
        raise HTTPException(status_code=400, detail="Срок действия кода истёк")

    # Compare codes
    if user.sms_code != verify_data.code:
        raise HTTPException(status_code=400, detail="Неверный код")

    # Code is valid - mark as verified if not already
    if not user.is_verified:
        user.is_verified = True
    
    # Clear SMS code after successful verification
    user.sms_code = None
    user.sms_code_expires_at = None
    db.commit()

    # Create session and set cookie
    token = create_session(db, user.id)

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
    db: Session = Depends(get_db),
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
        db: Database session
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
    user = get_user_by_phone(db, sms_data.phone)
    
    if not user:
        # User not found - frontend should trigger registration
        raise HTTPException(status_code=404, detail="User not found")
    
    # User exists - send SMS code (for both verified and not verified)
    # This handles Scenario 3 (verified, no cookie) and Scenario 4 (not verified)
    
    # Generate and save code
    code = generate_sms_code()
    user.sms_code = code
    user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
    db.commit()
    
    # Send SMS
    sms_sent = send_sms(user.phone, code)
    
    if not sms_sent:
        raise HTTPException(status_code=500, detail="Failed to send SMS")
    
    return SMSResponse(sent=True)


@router.post("/api/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Logout user (delete session).
    
    Logic:
    - Get session token from cookie
    - Delete session from database
    - Clear cookie in browser
    
    Args:
        request: FastAPI request object (for cookie access)
        db: Database session
    
    Returns:
        {"success": true} if logged out successfully
    """
    # Get token from cookie
    token = request.cookies.get(COOKIE_NAME)
    
    if token:
        # Delete session from database
        delete_session(db, token)
    
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
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user.
    
    Logic:
    - Middleware already validated session and set request.state.current_user
    - Just return the user if authenticated
    
    Args:
        request: FastAPI request object (for cookie access)
        db: Database session
    
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
