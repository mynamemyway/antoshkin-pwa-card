"""
Unit tests for session_service.py

Tests session creation, retrieval, deletion, and cleanup functions.
"""

import pytest
from datetime import datetime, timedelta
from app.services.session_service import (
    create_session,
    get_session_by_token,
    delete_session,
    cleanup_expired_sessions,
    delete_all_user_sessions,
)
from app.models import User, Session


class TestCreateSession:
    """Tests for create_session() function."""

    @pytest.mark.asyncio
    async def test_create_session(self, db, test_user):
        """A.3.1: Создание сессии."""
        token = await create_session(db, test_user.id)

        assert token is not None
        assert len(token) > 0

        # Verify session in database
        session = db.query(Session).filter(Session.token == token).first()
        assert session is not None
        assert session.user_id == test_user.id
        assert session.token == token
        # Check expiration is ~30 days from now
        expected_expires = datetime.utcnow() + timedelta(days=30)
        assert abs((session.expires_at - expected_expires).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_create_session_custom_expiry(self, db, test_user):
        """A.3.2: Создание сессии с кастомным сроком."""
        token = await create_session(db, test_user.id, expires_in_days=7)

        session = db.query(Session).filter(Session.token == token).first()
        assert session is not None
        # Check expiration is ~7 days from now
        expected_expires = datetime.utcnow() + timedelta(days=7)
        assert abs((session.expires_at - expected_expires).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_create_session_multiple(self, db, test_user):
        """Создание нескольких сессий для одного пользователя."""
        token1 = await create_session(db, test_user.id)
        token2 = await create_session(db, test_user.id)

        assert token1 != token2

        sessions = db.query(Session).filter(Session.user_id == test_user.id).all()
        assert len(sessions) == 2


class TestGetSessionByToken:
    """Tests for get_session_by_token() function."""

    @pytest.mark.asyncio
    async def test_get_session_by_token_valid(self, db, test_session):
        """A.3.3: Получение валидной сессии."""
        session = await get_session_by_token(db, test_session.token)

        assert session is not None
        assert session.token == test_session.token
        assert session.user_id == test_session.user_id

    @pytest.mark.asyncio
    async def test_get_session_by_token_invalid(self, db):
        """A.3.4: Получение несуществующей сессии."""
        session = await get_session_by_token(db, "nonexistent_token")
        assert session is None

    @pytest.mark.asyncio
    async def test_get_session_by_token_expired(self, db, expired_session):
        """Получение просроченной сессии."""
        session = await get_session_by_token(db, expired_session.token)

        assert session is not None
        assert session.token == expired_session.token
        # Note: get_session_by_token doesn't check expiration
        assert session.is_valid() is False


class TestDeleteSession:
    """Tests for delete_session() function."""

    @pytest.mark.asyncio
    async def test_delete_session(self, db, test_session):
        """A.3.5: Удаление сессии."""
        result = await delete_session(db, test_session.token)

        assert result is True

        # Verify session is deleted
        session = db.query(Session).filter(Session.token == test_session.token).first()
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, db):
        """A.3.6: Удаление несуществующей сессии."""
        result = await delete_session(db, "nonexistent_token")
        assert result is False


class TestSessionIsValid:
    """Tests for Session.is_valid() method."""

    def test_session_is_valid(self, db, test_session):
        """A.3.7: Проверка валидности сессии - валидна."""
        assert test_session.is_valid() is True

    def test_session_is_expired(self, db, expired_session):
        """Проверка валидности сессии - просрочена."""
        assert expired_session.is_valid() is False


class TestCleanupExpiredSessions:
    """Tests for cleanup_expired_sessions() function."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, db, test_user, expired_session):
        """A.3.8: Очистка просроченных сессий."""
        # Create valid session
        await create_session(db, test_user.id)

        # Delete expired sessions
        deleted_count = await cleanup_expired_sessions(db)

        assert deleted_count >= 1

        # Verify only valid sessions remain
        sessions = db.query(Session).all()
        for session in sessions:
            assert session.is_valid() is True

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_none(self, db, test_user):
        """Очистка когда нет просроченных сессий."""
        # Create valid session only
        await create_session(db, test_user.id)

        deleted_count = await cleanup_expired_sessions(db)
        assert deleted_count == 0


class TestDeleteAllUserSessions:
    """Tests for delete_all_user_sessions() function."""

    @pytest.mark.asyncio
    async def test_delete_all_user_sessions(self, db, test_user):
        """A.3.9: Удаление всех сессий пользователя."""
        # Create multiple sessions
        await create_session(db, test_user.id)
        await create_session(db, test_user.id)
        await create_session(db, test_user.id)

        # Delete all sessions
        deleted_count = await delete_all_user_sessions(db, test_user.id)

        assert deleted_count == 3

        # Verify no sessions remain
        sessions = db.query(Session).filter(Session.user_id == test_user.id).all()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_delete_all_user_sessions_none(self, db, test_user):
        """Удаление сессий когда их нет."""
        deleted_count = await delete_all_user_sessions(db, test_user.id)
        assert deleted_count == 0
