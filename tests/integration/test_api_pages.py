"""
Integration tests for API page endpoints.

Tests /, /verify, /splash, /health endpoints.
"""

import pytest


class TestApiPages:
    """Tests for page endpoints."""

    def test_root_page(self, client):
        """B.7.1: Доступ к главной странице."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert b"Регистрация" in response.content
        assert b"Антошкин дворик" in response.content

    def test_verify_page(self, client):
        """B.7.2: Доступ к странице верификации."""
        response = client.get("/verify")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert b"Подтверждение кода" in response.content

    def test_splash_page(self, client):
        """B.7.3: Доступ к splash screen."""
        response = client.get("/splash")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert b"Антошкин дворик" in response.content

    def test_health_check(self, client):
        """B.7.4: Проверка health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
