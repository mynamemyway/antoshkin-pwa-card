"""
Pytest fixtures for all tests.

Provides:
- Database session (in-memory SQLite)
- TestClient for API requests
- Test users and sessions
- Mocked SMS service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User, Session
from app.config import settings

# Test configuration
TEST_DATABASE_URL = "sqlite:///./test.db"
TEST_PHONE = "+79991234567"
TEST_PHONE_ALT = "+79999876543"
TEST_FULL_NAME = "Тест Пользователь"
TEST_SMS_CODE = "0000"


@pytest.fixture(scope="session")
def test_engine():
    """
    Create in-memory SQLite database engine for tests.
    
    Uses check_same_thread=False for SQLite compatibility.
    Database is created once per test session.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(test_engine):
    """
    Create database session for each test function.
    
    Automatically rolls back all changes after test completion
    to ensure test isolation.
    
    Usage:
        def test_something(db):
            user = User(full_name="Test", phone="+79991234567")
            db.add(user)
            db.commit()
    """
    SessionTesting = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    
    session = SessionTesting()
    
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    try:
        yield session
    finally:
        # Rollback all changes after test
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db):
    """
    Create TestClient for API requests with database dependency override.
    
    All database operations in the app will use the test database session.
    Automatically closes client after test completion.
    
    Usage:
        def test_api_endpoint(client):
            response = client.get("/")
            assert response.status_code == 200
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Remove override after test
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db):
    """
    Create verified test user in database.
    
    Default phone: +79991234567
    Default name: Тест Пользователь
    
    Usage:
        def test_with_user(client, test_user):
            response = client.get(f"/card/{test_user.phone}")
    """
    user = User(
        full_name=TEST_FULL_NAME,
        phone=TEST_PHONE,
        is_verified=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    # Cleanup
    db.delete(user)
    db.commit()


@pytest.fixture(scope="function")
def test_user_unverified(db):
    """
    Create unverified test user in database.
    
    Phone: +79999876543 (different from default test_user)
    
    Usage:
        def test_unverified_user(client, test_user_unverified):
            assert test_user_unverified.is_verified == False
    """
    user = User(
        full_name="Неверифицированный Тест",
        phone=TEST_PHONE_ALT,
        is_verified=False,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    # Cleanup
    db.delete(user)
    db.commit()


@pytest.fixture(scope="function")
def test_session(db, test_user):
    """
    Create valid test session for test_user.
    
    Session expires in 30 days.
    Token is accessible via test_session.token.
    
    Usage:
        def test_authenticated_request(client, test_session):
            response = client.get(
                "/api/me",
                cookies={"session_token": test_session.token}
            )
    """
    session = Session(
        user_id=test_user.id,
        token="test_token_12345",
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    yield session
    # Cleanup
    db.delete(session)
    db.commit()


@pytest.fixture(scope="function")
def expired_session(db, test_user):
    """
    Create expired test session for test_user.
    
    Session expired 1 day ago.
    
    Usage:
        def test_expired_session(client, expired_session):
            response = client.get(
                "/api/me",
                cookies={"session_token": expired_session.token}
            )
            assert response.status_code == 401
    """
    session = Session(
        user_id=test_user.id,
        token="expired_token_67890",
        expires_at=datetime.utcnow() - timedelta(days=1)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    yield session
    # Cleanup
    db.delete(session)
    db.commit()


@pytest.fixture(scope="function")
def mock_sms_success():
    """
    Mock SMS sending service to always succeed.
    
    Patches send_sms() to return (True, "SMS sent").
    Use this for tests that don't need to test SMS service itself.
    
    Usage:
        def test_registration_with_sms(client, mock_sms_success):
            response = client.post("/api/send-sms", json={...})
            assert response.status_code == 200
    """
    with patch('app.api.routers.send_sms', return_value=(True, "SMS sent")) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_sms_failure():
    """
    Mock SMS sending service to always fail.
    
    Patches send_sms() to return (False, "SMS failed").
    Use this for testing error handling.
    
    Usage:
        def test_registration_sms_failure(client, mock_sms_failure):
            response = client.post("/api/send-sms", json={...})
            assert response.status_code == 500
    """
    with patch('app.api.routers.send_sms', return_value=(False, "SMS failed")) as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_sms_code():
    """
    Mock SMS code generation to return fixed code.
    
    Patches generate_sms_code() to always return "1234".
    Use this for predictable verification tests.
    
    Usage:
        def test_verify_with_known_code(client, mock_sms_code):
            # Code is always "1234"
            response = client.post("/api/verify", json={
                "phone": "+79991234567",
                "code": "1234"
            })
    """
    with patch('app.api.routers.generate_sms_code', return_value="1234") as mock:
        yield mock


@pytest.fixture
def auth_headers(test_session):
    """
    Return headers with valid session cookie for authenticated requests.
    
    Usage:
        def test_protected_endpoint(client, auth_headers):
            response = client.get(
                "/api/me",
                cookies=auth_headers
            )
    """
    return {"session_token": test_session.token}


@pytest.fixture(scope="function")
def many_users(db):
    """
    Create 100 test users for pagination testing.
    
    Users are named "User 1", "User 2", etc.
    Phones are +79990000001, +79990000002, etc.
    Every 3rd user is verified.
    
    Usage:
        def test_pagination(client, many_users):
            response = client.get("/admin?page=1")
            assert len(response_data["users"]) == 50
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
    
    db.commit()
    yield users
    # Cleanup
    for user in users:
        db.delete(user)
    db.commit()
