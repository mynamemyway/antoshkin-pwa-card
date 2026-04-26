"""
Integration tests for API SMS sending endpoint.

Tests /api/send-sms endpoint functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models import User
from datetime import timedelta, datetime
from sqlalchemy import select


class TestApiSendSms:
    """Tests for POST /api/send-sms endpoint."""

    def test_send_sms_success(self, client, test_user, mock_sms_success):
        """B.2.1: Успешная отправка SMS."""
        from app.config import settings

        # For check_call mode, use universal endpoint
        if settings.AUTH_METHOD == "check_call":
            response = client.post("/api/auth/initiate", json={
                "phone": test_user.phone
            })
        else:
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
        from app.config import settings

        # For check_call mode, use universal endpoint
        if settings.AUTH_METHOD == "check_call":
            response = client.post("/api/auth/initiate", json={
                "phone": test_user.phone
            })
        else:
            monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
            response = client.post("/api/send-sms", json={
                "phone": test_user.phone
            })

        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is True

    def test_send_sms_verified_user(self, client, test_user, mock_sms_success):
        """B.2.4: Отправка верифицированному пользователю."""
        from app.config import settings

        # test_user is already verified
        # For check_call mode, use universal endpoint
        if settings.AUTH_METHOD == "check_call":
            response = client.post("/api/auth/initiate", json={
                "phone": test_user.phone
            })
        else:
            response = client.post("/api/send-sms", json={
                "phone": test_user.phone
            })

        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is True

    @pytest.mark.asyncio
    async def test_send_sms_code_saved(self, client, test_user_unverified, mock_sms_success, db):
        """B.2.5: Проверка сохранения кода в БД."""
        from app.config import settings

        # Используем test_user_unverified чтобы проверить что is_verified=False после initiate
        # For check_call mode, use universal endpoint
        if settings.AUTH_METHOD == "check_call":
            response = client.post("/api/auth/initiate", json={
                "phone": test_user_unverified.phone
            })
        else:
            response = client.post("/api/send-sms", json={
                "phone": test_user_unverified.phone
            })

        assert response.status_code == 200

        # Verify verification data is saved in database
        result = await db.execute(select(User).where(User.phone == test_user_unverified.phone))
        user = result.scalar_one_or_none()

        # For check_call mode: user should have sms_check_id saved (NOT verified yet)
        # Verification happens only after simulate-call endpoint is invoked
        if settings.AUTH_METHOD == "check_call":
            # In check_call mode, initiation saves sms_check_id but does NOT verify
            assert user.sms_check_id is not None, "sms_check_id should be saved after initiate"
            assert user.is_verified is False, "User should NOT be verified until simulate-call is called"
        else:
            # For SMS/Flash Call mode: sms_code should be set
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

    @pytest.mark.asyncio
    async def test_send_sms_sms_failure(self, client, test_user, monkeypatch):
        """Отправка SMS при сбое сервиса."""
        # Disable test mode to use real send_sms flow
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', False)

        # Mock httpx.AsyncClient to simulate SMS.ru API failure
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ERROR", "status_message": "Insufficient funds"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('app.services.sms_service.httpx.AsyncClient', return_value=mock_client):
            response = client.post("/api/send-sms", json={
                "phone": test_user.phone
            })

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        # Error message now comes directly from SMS.ru API
        assert "SMS.ru error" in data["detail"] or "Failed to send SMS" in data["detail"]