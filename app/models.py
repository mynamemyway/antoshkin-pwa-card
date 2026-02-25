# app/models.py

"""
SQLAlchemy database models.

Defines the structure of database tables as Python classes.
Each class represents a table, each attribute represents a column.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

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
        created_at (datetime): Registration timestamp (auto-generated)
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
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        """String representation for debugging."""
        return f"<User(id={self.id}, phone='{self.phone}', verified={self.is_verified})>"
