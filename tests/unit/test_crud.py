"""
Unit tests for crud.py

Tests CRUD operations for User model.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.services.crud import (
    get_user_by_phone,
    get_user_by_id,
    create_user,
    update_user,
    get_all_users,
    count_users,
    delete_user,
    set_sms_code,
    clear_sms_code,
    verify_user
)
from app.models import User


class TestGetUserByPhone:
    """Tests for get_user_by_phone() function."""

    def test_get_user_by_phone_found(self, db, test_user):
        """A.4.1: Поиск существующего пользователя."""
        user = get_user_by_phone(db, test_user.phone)
        
        assert user is not None
        assert user.phone == test_user.phone
        assert user.full_name == test_user.full_name

    def test_get_user_by_phone_not_found(self, db):
        """A.4.2: Поиск несуществующего пользователя."""
        user = get_user_by_phone(db, "+79990000000")
        assert user is None


class TestGetUserById:
    """Tests for get_user_by_id() function."""

    def test_get_user_by_id_found(self, db, test_user):
        """A.4.3: Поиск по ID."""
        user = get_user_by_id(db, test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.phone == test_user.phone

    def test_get_user_by_id_not_found(self, db):
        """A.4.4: Поиск по несуществующему ID."""
        user = get_user_by_id(db, 99999)
        assert user is None


class TestCreateUser:
    """Tests for create_user() function."""

    def test_create_user(self, db):
        """A.4.5: Создание нового пользователя."""
        user = create_user(db, "Новый Пользователь", "+79991112233")
        
        assert user is not None
        assert user.id is not None
        assert user.full_name == "Новый Пользователь"
        assert user.phone == "+79991112233"
        assert user.is_verified is False
        assert user.created_at is not None

    def test_create_user_duplicate_phone(self, db, test_user):
        """A.4.6: Создание с дубликатом телефона."""
        with pytest.raises(IntegrityError):
            create_user(db, "Другой Пользователь", test_user.phone)


class TestUpdateUser:
    """Tests for update_user() function."""

    def test_update_user(self, db, test_user):
        """A.4.7: Обновление данных пользователя."""
        updated = update_user(db, test_user, {"full_name": "Обновлённое Имя"})
        
        assert updated.full_name == "Обновлённое Имя"
        assert updated.phone == test_user.phone  # Unchanged

    def test_update_user_verify(self, db, test_user_unverified):
        """Обновление статуса верификации."""
        updated = update_user(db, test_user_unverified, {"is_verified": True})
        
        assert updated.is_verified is True


class TestGetAllUsers:
    """Tests for get_all_users() function."""

    def test_get_all_users(self, db, many_users):
        """A.4.8: Получение списка пользователей."""
        users = get_all_users(db, limit=100)
        
        assert len(users) == 100
        # Check ordering (newest first)
        for i in range(len(users) - 1):
            assert users[i].created_at >= users[i + 1].created_at

    def test_get_all_users_pagination(self, db, many_users):
        """A.4.9: Пагинация списка."""
        users_page1 = get_all_users(db, limit=50, offset=0)
        users_page2 = get_all_users(db, limit=50, offset=50)
        
        assert len(users_page1) == 50
        assert len(users_page2) == 50
        # No overlap
        page1_ids = {u.id for u in users_page1}
        page2_ids = {u.id for u in users_page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_get_all_users_empty(self, db):
        """Получение списка когда пользователей нет."""
        users = get_all_users(db)
        assert len(users) == 0


class TestCountUsers:
    """Tests for count_users() function."""

    def test_count_users(self, db, many_users):
        """A.4.10: Подсчёт количества пользователей."""
        count = count_users(db)
        assert count == 100

    def test_count_users_empty(self, db):
        """Подсчёт когда пользователей нет."""
        count = count_users(db)
        assert count == 0


class TestDeleteUser:
    """Tests for delete_user() function."""

    def test_delete_user(self, db, test_user):
        """A.4.11: Удаление пользователя."""
        result = delete_user(db, test_user)
        
        assert result is True
        
        # Verify user is deleted
        user = get_user_by_phone(db, test_user.phone)
        assert user is None

    def test_delete_user_cascades_sessions(self, db, test_user, test_session):
        """Удаление пользователя удаляет сессии."""
        # Verify session exists
        sessions_before = db.query(Session).filter(Session.user_id == test_user.id).all()
        assert len(sessions_before) == 1
        
        # Delete user
        delete_user(db, test_user)
        
        # Verify sessions are deleted
        sessions_after = db.query(Session).filter(Session.user_id == test_user.id).all()
        assert len(sessions_after) == 0


class TestVerifyUser:
    """Tests for verify_user() function."""

    def test_verify_user(self, db, test_user_unverified):
        """A.4.12: Верификация пользователя."""
        # Set SMS code first
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow()
        db.commit()
        
        verified = verify_user(db, test_user_unverified)
        
        assert verified.is_verified is True
        assert verified.sms_code is None
        assert verified.sms_code_expires_at is None


class TestSetSmsCode:
    """Tests for set_sms_code() function."""

    def test_set_sms_code(self, db, test_user_unverified):
        """A.4.13: Установка SMS-кода."""
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        updated = set_sms_code(db, test_user_unverified, "1234", expires_at)
        
        assert updated.sms_code == "1234"
        assert updated.sms_code_expires_at == expires_at


class TestClearSmsCode:
    """Tests for clear_sms_code() function."""

    def test_clear_sms_code(self, db, test_user_unverified):
        """A.4.14: Очистка SMS-кода."""
        # Set SMS code first
        test_user_unverified.sms_code = "1234"
        test_user_unverified.sms_code_expires_at = datetime.utcnow()
        db.commit()
        
        updated = clear_sms_code(db, test_user_unverified)
        
        assert updated.sms_code is None
        assert updated.sms_code_expires_at is None


# Import Session for cascade test
from app.models import Session
