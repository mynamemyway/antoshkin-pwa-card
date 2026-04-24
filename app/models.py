# app/models.py

"""
SQLAlchemy database models.

Defines the structure of database tables as Python classes.
Each class represents a table, each attribute represents a column.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    User model for storing customer loyalty card data.

    Table: users

    Attributes:
        id (int): Primary key, auto-increment
        full_name (str): Customer's full name (max 100 characters)
        phone (str): Normalized phone number (+7XXXXXXXXXX format, unique)
        is_verified (bool): SMS verification status (default: False)
        sms_code (str): 4-digit verification code (temporary, nullable)
        sms_code_expires_at (datetime): Code expiration time (nullable)
        sms_check_id (str): Check Call verification ID from SMS.ru (nullable)
        is_privacy_accepted (bool): Privacy policy acceptance status (default: False)
        is_subscribed (bool): Subscription status (default: False)
        created_at (datetime): Registration timestamp (auto-generated)
        sessions (list): Relationship to Session objects (auto-delete on user delete)
    """

    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Customer information
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)

    # Verification status
    is_verified = Column(Boolean, default=False, nullable=False)

    # SMS verification code (temporary storage)
    sms_code = Column(String(4), nullable=True)
    sms_code_expires_at = Column(DateTime, nullable=True)

    # Check Call verification ID from SMS.ru
    sms_check_id = Column(String(50), nullable=True)

    # Privacy and subscription flags
    is_privacy_accepted = Column(Boolean, default=False, nullable=False)
    is_subscribed = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to Session objects
    # cascade="all, delete-orphan" ensures sessions are deleted when user is deleted
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        """String representation for debugging."""
        return f"<User(id={self.id}, phone='{self.phone}', verified={self.is_verified})>"


class Session(Base):
    """
    Session model for storing user authentication tokens.

    Table: sessions

    Attributes:
        id (int): Primary key, auto-increment
        user_id (int): Foreign key to users.id (indexed for fast lookups)
        token (str): Unique session token (UUID v4, indexed for fast lookups)
        expires_at (datetime): Session expiration time (30 days from creation)
        created_at (datetime): Session creation timestamp (auto-generated)
        user (User): Relationship to User object

    Usage:
        # Create session for user
        session = Session(user_id=1)
        db.add(session)
        db.commit()

        # Find session by token
        session = db.query(Session).filter(Session.token == token).first()

        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            # Session expired
    """

    __tablename__ = "sessions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key to users table
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Session token (generated with secrets.token_urlsafe(32))
    token = Column(String(255), unique=True, index=True, nullable=False)

    # Session expiration (30 days from creation)
    expires_at = Column(DateTime, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to User object
    user = relationship("User", back_populates="sessions")

    def __init__(self, **kwargs):
        """
        Initialize session with auto-generated token and expiration.

        Args:
            **kwargs: Keyword arguments (user_id required)
        """
        super().__init__(**kwargs)
        # Generate unique token if not provided
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(32)
        # Set expiration to 30 days from now if not provided
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=30)

    def is_valid(self) -> bool:
        """
        Check if session is still valid (not expired).

        Returns:
            True if session is valid, False if expired
        """
        return datetime.utcnow() < self.expires_at

    def __repr__(self):
        """String representation for debugging."""
        return f"<Session(id={self.id}, user_id={self.user_id}, token='{self.token[:8]}...', expires_at={self.expires_at})>"
        