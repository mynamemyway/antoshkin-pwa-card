"""
Integration tests for API registration endpoint.

Tests /api/register endpoint functionality.
"""

import pytest
from app.models import User


class TestApiRegister:
    """Tests for POST /api/register endpoint."""

    def test_register_new_user(self, client, mock_sms_success):
        """B.1.1: Регистрация нового пользователя."""
        response = client.post("/api/register", json={
            "full_name": "Новый Пользователь",
            "phone": "+79991112233"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Новый Пользователь"
        assert data["phone"] == "+79991112233"
        assert data["is_verified"] is False
        assert "id" in data
        assert "created_at" in data

    def test_register_existing_user(self, client, test_user):
        """B.1.2: Регистрация существующего пользователя."""
        response = client.post("/api/register", json={
            "full_name": "Другое Имя",
            "phone": test_user.phone
        })
        
        assert response.status_code == 200
        data = response.json()
        # Returns existing user data, not new name
        assert data["full_name"] == test_user.full_name
        assert data["id"] == test_user.id

    def test_register_invalid_phone(self, client):
        """B.1.3: Регистрация с неверным телефоном."""
        response = client.post("/api/register", json={
            "full_name": "Тест",
            "phone": "12345"
        })
        
        assert response.status_code == 422

    def test_register_missing_name(self, client):
        """B.1.4: Регистрация без имени."""
        response = client.post("/api/register", json={
            "phone": "+79991112233"
        })
        
        assert response.status_code == 422

    def test_register_missing_phone(self, client):
        """B.1.5: Регистрация без телефона."""
        response = client.post("/api/register", json={
            "full_name": "Тест"
        })
        
        assert response.status_code == 422

    def test_register_phone_format_plus7(self, client, mock_sms_success):
        """B.1.6: Телефон в формате +7XXXXXXXXXX."""
        response = client.post("/api/register", json={
            "full_name": "Тест",
            "phone": "+79991112233"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "+79991112233"

    def test_register_phone_format_8(self, client, mock_sms_success):
        """B.1.7: Телефон в формате 8XXXXXXXXXX."""
        response = client.post("/api/register", json={
            "full_name": "Тест",
            "phone": "89991112233"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Should be normalized to +7
        assert data["phone"] == "+79991112233"

    def test_register_phone_format_7(self, client, mock_sms_success):
        """B.1.8: Телефон в формате 7XXXXXXXXXX."""
        response = client.post("/api/register", json={
            "full_name": "Тест",
            "phone": "79991112233"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Should be normalized to +7
        assert data["phone"] == "+79991112233"

    def test_register_phone_formatted(self, client, mock_sms_success):
        """Регистрация с форматированным номером."""
        response = client.post("/api/register", json={
            "full_name": "Тест",
            "phone": "+7 (999) 111-22-33"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Should be normalized
        assert data["phone"] == "+79991112233"
