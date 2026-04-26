"""
Pytest fixtures for all tests.

Provides:
- Async database session (SQLite file-based for compatibility with app.main)
- TestClient for API requests
- Test users and sessions
- Mocked SMS service
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Create temp database file for tests
TEST_DB_FILE = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
TEST_DB_FILE.close()
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.name}"

# Set test database URL BEFORE importing app modules
os.environ["DATABASE_URL"] = TEST_DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")
os.environ["SMS_TEST_MODE"] = "True"

# Import models FIRST to register them with Base
from app.models import User, Session

# Reload settings to use test DATABASE_URL
from app import config
config.settings = config.Settings()

from app.database import Base, get_async_db

# Import app after settings override - this creates tables in test DB
from app.main import app

# Test configuration
TEST_PHONE = "+79991234567"
TEST_PHONE_ALT = "+79999876543"
TEST_FULL_NAME = "Тест Пользователь"
TEST_SMS_CODE = "0000"


@pytest.fixture(scope="function")
async def db():
    """
    Create fresh async database session for each test function.

    Uses file-based SQLite for compatibility with app.main.
    Database is cleaned between tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    # Drop all tables and recreate (clean slate for each test)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()


@pytest.fixture(scope="function")
async def client(db):
    """
    Create TestClient for API requests with async database dependency override.
    """
    async def override_get_async_db():
        yield db

    app.dependency_overrides[get_async_db] = override_get_async_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(db):
    """
    Create verified test user in database.
    """
    user = User(
        full_name=TEST_FULL_NAME,
        phone=TEST_PHONE,
        is_verified=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    yield user


@pytest.fixture(scope="function")
async def test_user_unverified(db):
    """
    Create unverified test user in database.
    """
    user = User(
        full_name="Неверифицированный Тест",
        phone=TEST_PHONE_ALT,
        is_verified=False,
        created_at=datetime.utcnow()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    yield user


@pytest.fixture(scope="function")
async def test_session(db, test_user):
    """
    Create valid test session for test_user.
    """
    session = Session(
        user_id=test_user.id,
        token="test_token_12345",
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    yield session


@pytest.fixture(scope="function")
async def expired_session(db, test_user):
    """
    Create expired test session for test_user.
    """
    session = Session(
        user_id=test_user.id,
        token="expired_token_67890",
        expires_at=datetime.utcnow() - timedelta(days=1)
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    yield session


@pytest.fixture(scope="function")
def mock_sms_success():
    """Mock SMS sending service to always succeed."""
    with patch('app.services.sms_service.send_sms', new_callable=AsyncMock, return_value=(True, "SMS sent")) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_sms_failure():
    """Mock SMS sending service to always fail."""
    with patch('app.services.sms_service.send_sms', new_callable=AsyncMock, return_value=(False, "SMS failed")) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_sms_code():
    """Mock SMS code generation to return fixed code."""
    with patch('app.services.auth_dispatcher.generate_sms_code', return_value="1234") as mock:
        yield mock


@pytest.fixture
def auth_headers(test_session):
    """Return headers with valid session cookie for authenticated requests."""
    return {"session_token": test_session.token}


@pytest.fixture(scope="function")
async def many_users(db):
    """
    Create 100 test users for pagination testing.
    """
    users = []
    for i in range(1, 101):
        user = User(
            full_name=f"User {i}",
            phone=f"+799900000{i:02d}",
            is_verified=(i % 3 == 0),
            created_at=datetime.utcnow() - timedelta(days=100-i)
        )
        db.add(user)
        users.append(user)

    await db.commit()
    yield users


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """
    Clean up test database file after all tests.
    """
    yield
    # Remove temp database file
    if os.path.exists(TEST_DB_FILE.name):
        os.unlink(TEST_DB_FILE.name)