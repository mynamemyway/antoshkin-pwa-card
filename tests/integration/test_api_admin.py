"""
Integration tests for API admin endpoints.

Tests /admin, /admin/export endpoints.
"""

import pytest
import csv
import io


class TestAdminPanel:
    """Tests for GET /admin endpoint."""

    def test_admin_panel_success(self, client):
        """B.5.1: Доступ к админ-панели."""
        response = client.get("/admin")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Админ-панель".encode('utf-8') in response.content

    def test_admin_panel_pagination(self, client, many_users):
        """B.5.2: Пагинация в админ-панели."""
        response = client.get("/admin?page=1")
        
        assert response.status_code == 200
        # Should show 50 users on first page
        assert b"User " in response.content

    def test_admin_panel_page_2(self, client, many_users):
        """B.5.3: Доступ ко второй странице."""
        response = client.get("/admin?page=2")
        
        assert response.status_code == 200
        # Should show users 51-100
        assert b"User " in response.content

    def test_admin_panel_search_found(self, client, test_user, db):
        """B.5.4: Поиск по телефону (найдено)."""
        response = client.get(f"/admin?search={test_user.phone}")
        
        assert response.status_code == 200
        # Check that user ID appears in the HTML
        assert str(test_user.id).encode() in response.content

    def test_admin_panel_search_not_found(self, client):
        """B.5.5: Поиск по телефону (не найдено)."""
        response = client.get("/admin?search=%2B79990000000")
        
        assert response.status_code == 200
        assert "Пользователей не найдено".encode('utf-8') in response.content

    def test_admin_panel_search_partial(self, client, many_users):
        """B.5.6: Поиск по части номера."""
        response = client.get("/admin?search=99900000")
        
        assert response.status_code == 200
        # Should find all users with this pattern
        assert b"User " in response.content


class TestAdminExport:
    """Tests for GET /admin/export endpoint."""

    def test_admin_export_csv(self, client):
        """B.5.8: Экспорт в CSV."""
        response = client.get("/admin/export")
        
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment; filename=users.csv" in response.headers["content-disposition"]

    def test_admin_export_csv_content(self, client, test_user):
        """B.5.9: Проверка содержимого CSV."""
        response = client.get("/admin/export")
        
        assert response.status_code == 200
        
        # Parse CSV content
        content = response.content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        # Check header
        assert reader.fieldnames == ['id', 'full_name', 'phone', 'is_verified', 'created_at']
        
        # Check user data
        user_row = next((r for r in rows if r['phone'] == test_user.phone), None)
        assert user_row is not None
        assert user_row['full_name'] == test_user.full_name
        # Boolean in Python is capitalized (True/False)
        assert user_row['is_verified'] in ['True', 'False']
