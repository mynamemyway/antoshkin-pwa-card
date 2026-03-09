"""
Integration tests for API card endpoint.

Tests /card/{phone} endpoint.
"""

import pytest
from app.models import User


class TestApiCard:
    """Tests for GET /card/{phone} endpoint."""

    def test_card_page_success(self, client, test_user):
        """B.6.1: Доступ к карте верифицированного."""
        response = client.get(f"/card/{test_user.phone}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Ваша карта".encode('utf-8') in response.content
        assert test_user.full_name.encode('utf-8') in response.content

    def test_card_page_not_verified(self, client, test_user_unverified):
        """B.6.2: Доступ к карте неверифицированного."""
        response = client.get(f"/card/{test_user_unverified.phone}")
        
        assert response.status_code == 200
        # Should redirect to verify page (render verify template)
        assert "Подтверждение кода".encode('utf-8') in response.content

    def test_card_page_user_not_found(self, client):
        """B.6.3: Доступ к карте несуществующего."""
        response = client.get("/card/+79990000000")
        
        assert response.status_code == 404

    def test_card_page_qr_data(self, client, test_user):
        """B.6.4: Проверка данных QR-кода."""
        response = client.get(f"/card/{test_user.phone}")
        
        assert response.status_code == 200
        # Check that user data is passed to template
        assert test_user.phone.encode('utf-8') in response.content
        assert test_user.full_name.encode('utf-8') in response.content
