"""
Unit tests for sms_service.py

Tests SMS code generation, sending, and verification functions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.services.sms_service import (
    generate_sms_code,
    send_sms,
    verify_sms_code,
    set_user_sms_code,
    resend_sms_code,
    TEST_CODE
)
from app.models import User


class TestGenerateSmsCode:
    """Tests for generate_sms_code() function."""

    def test_generate_sms_code_test_mode(self, monkeypatch):
        """A.2.1: Генерация кода в тестовом режиме."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        result = generate_sms_code()
        assert result == "0000"

    def test_generate_sms_code_prod_mode(self, monkeypatch):
        """A.2.2: Генерация кода в боевом режиме."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', False)
        result = generate_sms_code()
        # Should be 4 digits
        assert len(result) == 4
        assert result.isdigit()

    def test_generate_sms_code_format(self, monkeypatch):
        """A.2.3: Формат кода - строка из 4 цифр."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', False)
        result = generate_sms_code()
        assert isinstance(result, str)
        assert len(result) == 4


class TestSendSms:
    """Tests for send_sms() function."""

    def test_send_sms_test_mode(self, monkeypatch, caplog):
        """Отправка SMS в тестовом режиме."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        success, message = send_sms("+79991234567", "1234")
        assert success is True
        assert "test mode" in message.lower()

    @patch('app.services.sms_service.requests.get')
    def test_send_sms_production_success(self, mock_get, monkeypatch):
        """Отправка SMS в боевом режиме - успех."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', False)
        monkeypatch.setattr('app.services.sms_service.settings.SMS_API_KEY', 'test_key')
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "OK"}
        mock_get.return_value = mock_response
        
        success, message = send_sms("+79991234567", "1234")
        assert success is True
        assert message == "SMS sent"

    @patch('app.services.sms_service.requests.get')
    def test_send_sms_production_error(self, mock_get, monkeypatch):
        """Отправка SMS в боевом режиме - ошибка."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', False)
        monkeypatch.setattr('app.services.sms_service.settings.SMS_API_KEY', 'test_key')
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ERROR", "status_message": "Invalid number"}
        mock_get.return_value = mock_response
        
        success, message = send_sms("+79991234567", "1234")
        assert success is False
        assert "error" in message.lower()

    @patch('app.services.sms_service.requests.get')
    def test_send_sms_timeout(self, mock_get, monkeypatch):
        """Отправка SMS - таймаут."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', False)
        monkeypatch.setattr('app.services.sms_service.settings.SMS_API_KEY', 'test_key')
        
        mock_get.side_effect = Exception("Timeout")
        
        success, message = send_sms("+79991234567", "1234")
        assert success is False


class TestVerifySmsCode:
    """Tests for verify_sms_code() function."""

    def test_verify_sms_code_valid(self, db):
        """A.2.4: Верификация верным кодом."""
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=False,
            sms_code="1234",
            sms_code_expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.add(user)
        db.commit()
        
        success, message = verify_sms_code(db, user, "1234")
        assert success is True
        assert message == "Verified"
        assert user.is_verified is True
        assert user.sms_code is None

    def test_verify_sms_code_invalid(self, db):
        """A.2.5: Верификация неверным кодом."""
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=False,
            sms_code="1234",
            sms_code_expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.add(user)
        db.commit()
        
        success, message = verify_sms_code(db, user, "5678")
        assert success is False
        assert "неверный" in message.lower()

    def test_verify_sms_code_expired(self, db):
        """A.2.6: Верификация просроченным кодом."""
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=False,
            sms_code="1234",
            sms_code_expires_at=datetime.utcnow() - timedelta(minutes=1)
        )
        db.add(user)
        db.commit()
        
        success, message = verify_sms_code(db, user, "1234")
        assert success is False
        assert "истёк" in message.lower()

    def test_verify_sms_code_already_verified(self, db):
        """A.2.7: Верификация верифицированного."""
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=True,
            sms_code=None,
            sms_code_expires_at=None
        )
        db.add(user)
        db.commit()
        
        success, message = verify_sms_code(db, user, "1234")
        assert success is True
        assert "already verified" in message.lower()

    def test_verify_sms_code_no_code(self, db):
        """A.2.8: Верификация без отправки кода."""
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=False,
            sms_code=None,
            sms_code_expires_at=None
        )
        db.add(user)
        db.commit()
        
        success, message = verify_sms_code(db, user, "1234")
        assert success is False
        assert "не был отправлен" in message.lower()


class TestSetUserSmsCode:
    """Tests for set_user_sms_code() function."""

    def test_set_user_sms_code(self, db, monkeypatch):
        """A.2.9: Установка SMS-кода."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=False
        )
        db.add(user)
        db.commit()
        
        success, code, message = set_user_sms_code(db, user)
        assert success is True
        assert code == "0000"  # Test mode
        assert user.sms_code == "0000"
        assert user.sms_code_expires_at is not None
        # Check expiration is ~5 minutes from now
        expected_expires = datetime.utcnow() + timedelta(minutes=5)
        assert abs((user.sms_code_expires_at - expected_expires).total_seconds()) < 2


class TestResendSmsCode:
    """Tests for resend_sms_code() function."""

    def test_resend_sms_code(self, db, monkeypatch):
        """A.2.10: Повторная отправка кода."""
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=False
        )
        db.add(user)
        db.commit()
        
        success, code, message = resend_sms_code(db, user)
        assert success is True
        assert code == "0000"
        assert user.sms_code == "0000"

    def test_resend_sms_code_verified(self, db):
        """A.2.11: Повторная отправка верифицированному."""
        user = User(
            full_name="Test User",
            phone="+79991234567",
            is_verified=True
        )
        db.add(user)
        db.commit()
        
        success, code, message = resend_sms_code(db, user)
        assert success is False
        assert code == ""
        assert "already verified" in message.lower()
