# app/services/session_service.py

"""
Session service for managing user authentication tokens.

Provides database operations for session lifecycle:
- create_session: Generate new session token for user
- get_session_by_token: Retrieve session by token (for auth)
- delete_session: Remove session (logout)
- cleanup_expired_sessions: Remove expired sessions (maintenance)

All sessions are stored in HttpOnly cookies (30-day lifetime).
Token is never exposed to JavaScript (XSS protection).
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Session


def create_session(db: Session, user_id: int, expires_in_days: int = 30) -> str:
    """
    Create new session for user and return token.
    
    Args:
        db: Database session
        user_id: ID of the user to create session for
        expires_in_days: Session lifetime in days (default: 30)
    
    Returns:
        Session token (string, 256-bit entropy via secrets.token_urlsafe)
    
    Usage:
        # Create session after successful login
        token = create_session(db, user_id=123)
        
        # Set cookie in response
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=2592000  # 30 days
        )
    
    Note:
        - Token is generated using secrets.token_urlsafe(32) for cryptographic security
        - Old sessions for the same user are NOT deleted (allows multiple devices)
        - Use cleanup_expired_sessions() periodically to remove old sessions
    """
    # Generate cryptographically secure token
    token = secrets.token_urlsafe(32)
    
    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Create session object
    db_session = Session(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    
    # Add to database
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    return token


def get_session_by_token(db: Session, token: str) -> Optional[Session]:
    """
    Retrieve session by token.
    
    Args:
        db: Database session
        token: Session token from cookie
    
    Returns:
        Session object if found and valid, None otherwise
    
    Usage:
        # In middleware or auth dependency
        token = request.cookies.get("session_token")
        session = get_session_by_token(db, token)
        
        if session and session.is_valid():
            # Authenticated user
            current_user = session.user
        else:
            # Invalid or expired session
            raise HTTPException(status_code=401)
    
    Note:
        - Does NOT check expiration (call session.is_valid() separately)
        - Returns None if token not found in database
    """
    # Query session by token
    session = db.query(Session).filter(Session.token == token).first()
    
    # Return session (caller should check session.is_valid())
    return session


def delete_session(db: Session, token: str) -> bool:
    """
    Delete session (logout user).
    
    Args:
        db: Database session
        token: Session token to delete
    
    Returns:
        True if session was deleted, False if not found
    
    Usage:
        # Logout endpoint
        token = request.cookies.get("session_token")
        delete_session(db, token)
        
        # Clear cookie in response
        response.delete_cookie("session_token")
    
    Note:
        - Deletes only the specific session (other device sessions remain active)
        - Returns True even if session was already expired
    """
    # Find session by token
    session = db.query(Session).filter(Session.token == token).first()
    
    if not session:
        return False
    
    # Delete session
    db.delete(session)
    db.commit()
    
    return True


def cleanup_expired_sessions(db: Session) -> int:
    """
    Remove all expired sessions from database.
    
    Args:
        db: Database session
    
    Returns:
        Number of sessions deleted
    
    Usage:
        # Run periodically (e.g., daily cron job)
        deleted_count = cleanup_expired_sessions(db)
        print(f"Cleaned up {deleted_count} expired sessions")
        
        # Or schedule with background task
        @app.on_event("startup")
        async def startup_event():
            # Run cleanup on startup (optional)
            cleanup_expired_sessions(db)
    
    Note:
        - Should be called periodically (e.g., daily) to prevent database bloat
        - Does NOT affect active sessions
        - Safe to call concurrently (DELETE with WHERE clause)
    """
    # Get current UTC time
    now = datetime.utcnow()
    
    # Delete expired sessions
    deleted_count = db.query(Session).filter(
        Session.expires_at < now
    ).delete()
    
    # Commit changes
    db.commit()
    
    return deleted_count


def delete_all_user_sessions(db: Session, user_id: int) -> int:
    """
    Delete all sessions for a specific user (force logout all devices).
    
    Args:
        db: Database session
        user_id: ID of the user
    
    Returns:
        Number of sessions deleted
    
    Usage:
        # Force logout after password change
        delete_all_user_sessions(db, user_id=123)
        
        # Or in security incident
        if suspicious_activity_detected:
            delete_all_user_sessions(db, user.id)
    
    Note:
        - Deletes ALL sessions for user (including valid ones)
        - User must re-authenticate on all devices
    """
    # Delete all sessions for user
    deleted_count = db.query(Session).filter(
        Session.user_id == user_id
    ).delete()
    
    # Commit changes
    db.commit()
    
    return deleted_count
