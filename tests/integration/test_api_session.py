"""
Integration tests for API session endpoints.

Tests /api/login, /api/logout, /api/me endpoints.
"""

import pytest
from datetime import datetime, timedelta
from app.models import User, Session


class TestApiLogin:
    """Tests for POST /api/login endpoint."""

    def test_login_success(self, client, test_user, mock_sms_success):
        """B.4.1: Успешный вход по телефону."""
        response = client.post("/api/login", json={
            "phone": test_user.phone
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is True

    def test_login_user_not_found(self, client, mock_sms_success):
        """B.4.2: Вход несуществующего пользователя."""
        response = client.post("/api/login", json={
            "phone": "+79990000000"
        })
        
        assert response.status_code == 404

    def test_login_saves_code(self, client, test_user, mock_sms_success):
        """Вход сохраняет код в БД."""
        response = client.post("/api/login", json={
            "phone": test_user.phone
        })
        
        assert response.status_code == 200
        
        # Verify code is saved
        db_user = client.app.state.db.query(User).filter(User.phone == test_user.phone).first()
        assert db_user.sms_code is not None


class TestApiLogout:
    """Tests for POST /api/logout endpoint."""

    def test_logout_success(self, client, test_session):
        """B.4.3: Успешный выход."""
        response = client.post(
            "/api/logout",
            cookies={"session_token": test_session.token}
        )
        
        assert response.status_code == 200
        
        # Verify session is deleted from database
        session = client.app.state.db.query(Session).filter(
            Session.token == test_session.token
        ).first()
        assert session is None

    def test_logout_no_cookie(self, client):
        """B.4.4: Выход без cookie."""
        response = client.post("/api/logout")
        
        assert response.status_code == 200

    def test_logout_clears_cookie(self, client, test_session):
        """Выход удаляет cookie."""
        response = client.post(
            "/api/logout",
            cookies={"session_token": test_session.token}
        )
        
        assert response.status_code == 200
        # Cookie should be cleared (empty value or expired)
        assert "session_token" in response.cookies


class TestApiMe:
    """Tests for GET /api/me endpoint."""

    def test_get_current_user_authenticated(self, client, test_session, auth_headers):
        """B.4.5: Получение текущего пользователя (авторизован)."""
        response = client.get(
            "/api/me",
            cookies=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == test_session.user.phone
        assert data["full_name"] == test_session.user.full_name

    def test_get_current_user_unauthenticated(self, client):
        """B.4.6: Получение текущего пользователя (не авторизован)."""
        response = client.get("/api/me")
        
        assert response.status_code == 401

    def test_get_current_user_expired_session(self, client, expired_session):
        """B.4.7: Сессия с истёкшим сроком."""
        response = client.get(
            "/api/me",
            cookies={"session_token": expired_session.token}
        )
        
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """B.4.8: Неверный токен сессии."""
        response = client.get(
            "/api/me",
            cookies={"session_token": "invalid_token"}
        )
        
        assert response.status_code == 401
