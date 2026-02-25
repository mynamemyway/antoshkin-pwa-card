# app/database.py

"""
Database configuration and session management.

Configures SQLAlchemy engine for SQLite database and provides
session factory for database operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Create SQLAlchemy engine
# For SQLite: add check_same_thread=False to allow multiple threads
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Create session factory
# SessionLocal() will create new database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for declarative models
# All models should inherit from this Base
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI to get database session.
    
    Yields:
        SQLAlchemy session for database operations
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
