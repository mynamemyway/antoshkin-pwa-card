# app/database.py

"""
Database configuration and session management.

Configures SQLAlchemy engine for SQLite database and provides
session factories for both synchronous and asynchronous database operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings

# =============================================================================
# Synchronous engine and session (for backward compatibility)
# =============================================================================

# Create SQLAlchemy engine
# For SQLite: add check_same_thread=False to allow multiple threads
sync_engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Create synchronous session factory
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Base class for declarative models
# All models should inherit from this Base
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI to get synchronous database session.

    Yields:
        SQLAlchemy session for database operations

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Asynchronous engine and session (for async endpoints)
# =============================================================================

# Convert DATABASE_URL for async: sqlite:/// → sqlite+aiosqlite:///
# This allows async operations with SQLite database
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "sqlite:///",
    "sqlite+aiosqlite:///"
)

# Create async engine
# echo=True for SQL query logging (disable in production)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,  # Set True for SQL debugging
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession
)


async def get_async_db():
    """
    Async dependency function for FastAPI to get async database session.

    Yields:
        AsyncSession for async database operations

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_async_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_db_readonly():
    """
    Async dependency for read-only database operations.

    Yields:
        AsyncSession with expire_on_commit=False for read operations

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_async_db_readonly)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

