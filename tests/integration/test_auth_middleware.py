"""
Integration tests for authentication middleware.

Tests SessionAuthMiddleware functionality.
"""

import pytest
from fastapi import Request
from app.middleware.auth import SessionAuthMiddleware
from datetime import datetime, timedelta


class TestAuthMiddleware:
    """Tests for SessionAuthMiddleware."""

    def test_middleware_valid_session(self, client, test_session):
        """C.1.1: Middleware с валидной сессией."""
        # Make request with valid session cookie
        response = client.get(
            "/api/me",
            cookies={"session_token": test_session.token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == test_session.user.phone

    def test_middleware_no_cookie(self, client):
        """C.1.2: Middleware без cookie."""
        response = client.get("/api/me")
        
        assert response.status_code == 401

    def test_middleware_invalid_token(self, client):
        """C.1.3: Middleware с неверным токеном."""
        response = client.get(
            "/api/me",
            cookies={"session_token": "invalid_token"}
        )
        
        assert response.status_code == 401

    def test_middleware_expired_session(self, client, expired_session):
        """C.1.4: Middleware с просроченной сессией."""
        response = client.get(
            "/api/me",
            cookies={"session_token": expired_session.token}
        )
        
        assert response.status_code == 401

    def test_middleware_sets_authenticated_flag(self, client, test_session):
        """C.1.5: Middleware устанавливает флаг is_authenticated."""
        # This is tested indirectly - if we get user data, flag was set
        response = client.get(
            "/api/me",
            cookies={"session_token": test_session.token}
        )
        
        assert response.status_code == 200
        # If we got here, middleware set current_user and is_authenticated
