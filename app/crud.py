# app/crud.py
"""
CRUD (Create, Read, Update, Delete) service for User model.

Provides database operations for user management:
- get_user_by_phone: Retrieve user by phone number
- create_user: Create new user
- update_user: Update user fields
- get_all_users: Get paginated user list
- delete_user: Remove user from database
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import User


def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """
    Get user by phone number.
    
    Args:
        db: Database session
        phone: Normalized phone number (+7XXXXXXXXXX)
    
    Returns:
        User object if found, None otherwise
    
    Usage:
        user = get_user_by_phone(db, "+79991234567")
        if user:
            print(f"Found: {user.full_name}")
    """
    return db.query(User).filter(User.phone == phone).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        db: Database session
        user_id: User's primary key
    
    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, full_name: str, phone: str) -> User:
    """
    Create new user in database.
    
    Args:
        db: Database session
        full_name: Customer's full name
        phone: Normalized phone number (+7XXXXXXXXXX)
    
    Returns:
        Created User object (with id and created_at populated)
    
    Usage:
        user = create_user(db, "Иван Иванов", "+79991234567")
        print(f"Created user with ID: {user.id}")
    """
    db_user = User(
        full_name=full_name,
        phone=phone,
        is_verified=False,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(
    db: Session,
    user: User,
    update_data: dict
) -> User:
    """
    Update user fields.
    
    Args:
        db: Database session
        user: User object to update
        update_data: Dictionary with fields to update
            e.g., {"full_name": "Новое имя", "is_verified": True}
    
    Returns:
        Updated User object
    
    Usage:
        user = get_user_by_phone(db, "+79991234567")
        updated = update_user(db, user, {"is_verified": True})
    """
    for key, value in update_data.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user


def get_all_users(
    db: Session,
    limit: int = 50,
    offset: int = 0
) -> List[User]:
    """
    Get paginated list of all users.
    
    Args:
        db: Database session
        limit: Maximum number of users to return (default: 50)
        offset: Number of users to skip (default: 0)
    
    Returns:
        List of User objects ordered by created_at (newest first)
    
    Usage:
        users = get_all_users(db, limit=10, offset=0)
        for user in users:
            print(f"{user.full_name}: {user.phone}")
    """
    return db.query(User)\
        .order_by(User.created_at.desc())\
        .offset(offset)\
        .limit(limit)\
        .all()


def count_users(db: Session) -> int:
    """
    Get total count of users in database.
    
    Args:
        db: Database session
    
    Returns:
        Total number of users
    
    Usage:
        total = count_users(db)
        print(f"Total users: {total}")
    """
    return db.query(User).count()


def delete_user(db: Session, user: User) -> bool:
    """
    Delete user from database.
    
    Args:
        db: Database session
        user: User object to delete
    
    Returns:
        True if deleted successfully
    
    Usage:
        user = get_user_by_phone(db, "+79991234567")
        delete_user(db, user)
    """
    db.delete(user)
    db.commit()
    return True


def set_sms_code(
    db: Session,
    user: User,
    code: str,
    expires_at: datetime
) -> User:
    """
    Set SMS verification code for user.
    
    Args:
        db: Database session
        user: User object
        code: 4-digit verification code
        expires_at: Code expiration timestamp
    
    Returns:
        Updated User object
    """
    user.sms_code = code
    user.sms_code_expires_at = expires_at
    db.commit()
    db.refresh(user)
    return user


def clear_sms_code(db: Session, user: User) -> User:
    """
    Clear SMS verification code after successful verification.
    
    Args:
        db: Database session
        user: User object
    
    Returns:
        Updated User object
    """
    user.sms_code = None
    user.sms_code_expires_at = None
    db.commit()
    db.refresh(user)
    return user


def verify_user(db: Session, user: User) -> User:
    """
    Mark user as verified and clear SMS code.
    
    Args:
        db: Database session
        user: User object to verify
    
    Returns:
        Updated User object with is_verified=True
    
    Usage:
        user = get_user_by_phone(db, "+79991234567")
        verified_user = verify_user(db, user)
    """
    user.is_verified = True
    user.sms_code = None
    user.sms_code_expires_at = None
    db.commit()
    db.refresh(user)
    return user
