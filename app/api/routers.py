# app/api/routers.py

"""
API routers for the loyalty card application.

Defines all HTTP endpoints for:
- User registration and verification
- SMS code sending and validation
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
from app.models import User
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

# Create router instance
router = APIRouter()


# ============== Helper Functions ==============
# Note: These functions are now imported from app.services
# Local definitions kept for backward compatibility (will be removed later)

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


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    """
    Admin panel - displays list of all users.
    
    Args:
        request: FastAPI request object
        db: Database session
    
    Returns:
        Rendered admin panel HTML template
    """
    users = db.query(User).order_by(User.created_at.desc()).limit(50).all()
    total = db.query(User).count()
    return request.state.templates.TemplateResponse(
        "admin.html",
        {"request": request, "users": users, "total": total}
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
    
    if user.is_verified:
        # User already verified, no need to send SMS
        return SMSResponse(sent=True)
    
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


@router.post("/api/verify", response_model=VerifyResponse)
async def verify_code(verify_data: UserVerify, db: Session = Depends(get_db)):
    """
    Verify SMS code and activate user account.
    
    Args:
        verify_data: Phone number and verification code
        db: Database session
    
    Returns:
        {"verified": true} if code is valid
    
    Raises:
        HTTPException: If user not found, code invalid, or expired
    """
    user = get_user_by_phone(db, verify_data.phone)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified:
        # Already verified
        return VerifyResponse(verified=True)
    
    # Check code and expiration
    if not user.sms_code:
        raise HTTPException(status_code=400, detail="No SMS code sent")
    
    if user.sms_code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="SMS code expired")
    
    if user.sms_code != verify_data.code:
        raise HTTPException(status_code=400, detail="Invalid SMS code")
    
    # Mark as verified
    user.is_verified = True
    user.sms_code = None
    user.sms_code_expires_at = None
    db.commit()
    
    return VerifyResponse(verified=True)
