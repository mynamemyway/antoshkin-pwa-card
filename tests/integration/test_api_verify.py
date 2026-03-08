"""
Integration tests for API verification endpoint.

Tests /api/verify endpoint functionality.
"""

import pytest
from datetime import datetime, timedelta
from app.models import User


class TestApiVerify:
    """Tests for POST /api/verify endpoint."""

    def test_verify_code_success(self, client, test_user_unverified, mock_sms_code):
        """B.3.1: Успешная верификация."""
        # Set SMS code
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        client.app.state.db.commit()
        
        response = client.post("/api/verify", json={
            "phone": test_user_unverified.phone,
            "code": "1234"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        
        # Check cookie is set
        assert "session_token" in response.cookies

    def test_verify_code_invalid(self, client, test_user_unverified):
        """B.3.2: Неверный код."""
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        client.app.state.db.commit()
        
        response = client.post("/api/verify", json={
            "phone": test_user_unverified.phone,
            "code": "5678"
        })
        
        assert response.status_code == 400

    def test_verify_code_expired(self, client, test_user_unverified):
        """B.3.3: Просроченный код."""
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow() - timedelta(minutes=1)
        client.app.state.db.commit()
        
        response = client.post("/api/verify", json={
            "phone": test_user_unverified.phone,
            "code": "1234"
        })
        
        assert response.status_code == 400

    def test_verify_code_not_found(self, client):
        """B.3.4: Верификация несуществующего пользователя."""
        response = client.post("/api/verify", json={
            "phone": "+79990000000",
            "code": "1234"
        })
        
        assert response.status_code == 404

    def test_verify_code_no_code_sent(self, client, test_user_unverified):
        """B.3.5: Верификация без отправки кода."""
        # Don't set sms_code
        response = client.post("/api/verify", json={
            "phone": test_user_unverified.phone,
            "code": "1234"
        })
        
        assert response.status_code == 400

    def test_verify_code_sets_cookie(self, client, test_user_unverified, mock_sms_code):
        """B.3.6: Проверка установки cookie."""
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        client.app.state.db.commit()
        
        response = client.post("/api/verify", json={
            "phone": test_user_unverified.phone,
            "code": "1234"
        })
        
        assert response.status_code == 200
        assert "session_token" in response.cookies
        cookie = response.cookies.get("session_token")
        assert cookie is not None
        assert len(cookie) > 0

    def test_verify_code_marks_user_verified(self, client, test_user_unverified, mock_sms_code):
        """B.3.7: Проверка статуса верификации."""
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        client.app.state.db.commit()
        
        response = client.post("/api/verify", json={
            "phone": test_user_unverified.phone,
            "code": "1234"
        })
        
        assert response.status_code == 200
        
        # Verify user is now verified in database
        db_user = client.app.state.db.query(User).filter(User.phone == test_user_unverified.phone).first()
        assert db_user.is_verified is True

    def test_verify_code_clears_sms_code(self, client, test_user_unverified, mock_sms_code):
        """B.3.8: Проверка очистки кода после верификации."""
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        client.app.state.db.commit()
        
        response = client.post("/api/verify", json={
            "phone": test_user_unverified.phone,
            "code": "1234"
        })
        
        assert response.status_code == 200
        
        # Verify SMS code is cleared
        db_user = client.app.state.db.query(User).filter(User.phone == test_user_unverified.phone).first()
        assert db_user.sms_code is None
        assert db_user.sms_code_expires_at is None

    def test_verify_already_verified_user(self, client, test_user, mock_sms_code):
        """B.3.9: Верификация верифицированного пользователя."""
        # Set SMS code for verified user (for re-login)
        test_user.sms_code = "1234"
        test_user.sms_code_expires_at = datetime.utcnow() + timedelta(minutes=5)
        client.app.state.db.commit()
        
        response = client.post("/api/verify", json={
            "phone": test_user.phone,
            "code": "1234"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
