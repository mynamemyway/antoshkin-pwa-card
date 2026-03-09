"""
Integration tests for API SMS sending endpoint.

Tests /api/send-sms endpoint functionality.
"""

import pytest
from app.models import User
from datetime import timedelta, datetime


class TestApiSendSms:
    """Tests for POST /api/send-sms endpoint."""

    def test_send_sms_success(self, client, test_user, mock_sms_success):
        """B.2.1: Успешная отправка SMS."""
        response = client.post("/api/send-sms", json={
            "phone": test_user.phone
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is True

    def test_send_sms_user_not_found(self, client, mock_sms_success):
        """B.2.2: Отправка несуществующему пользователю."""
        response = client.post("/api/send-sms", json={
            "phone": "+79990000000"
        })
        
        assert response.status_code == 404

    def test_send_sms_test_mode(self, client, test_user, monkeypatch):
        """B.2.3: Отправка в тестовом режиме."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        
        response = client.post("/api/send-sms", json={
            "phone": test_user.phone
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is True

    def test_send_sms_verified_user(self, client, test_user, mock_sms_success):
        """B.2.4: Отправка верифицированному пользователю."""
        # test_user is already verified
        response = client.post("/api/send-sms", json={
            "phone": test_user.phone
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is True

    def test_send_sms_code_saved(self, client, test_user, mock_sms_success, db):
        """B.2.5: Проверка сохранения кода в БД."""
        response = client.post("/api/send-sms", json={
            "phone": test_user.phone
        })
        
        assert response.status_code == 200
        
        # Verify code is saved in database
        user = db.query(User).filter(User.phone == test_user.phone).first()
        assert user.sms_code is not None
        assert user.sms_code_expires_at is not None
        # Check expiration is ~5 minutes from now
        expected_expires = datetime.utcnow() + timedelta(minutes=5)
        assert abs((user.sms_code_expires_at - expected_expires).total_seconds()) < 10

    def test_send_sms_invalid_phone(self, client, test_user):
        """B.2.6: Отправка с неверным телефоном."""
        response = client.post("/api/send-sms", json={
            "phone": "12345"
        })
        
        assert response.status_code == 422

    def test_send_sms_sms_failure(self, client, test_user, mock_sms_failure):
        """Отправка SMS при сбое сервиса."""
        response = client.post("/api/send-sms", json={
            "phone": test_user.phone
        })
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to send SMS" in data["detail"]
