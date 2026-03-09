"""
Unit tests for crud.py

Tests CRUD operations for User model.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
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
from app.models import User, Session


class TestGetUserByPhone:
    """Tests for get_user_by_phone() function."""

    @pytest.mark.asyncio
    async def test_get_user_by_phone_found(self, db, test_user):
        """A.4.1: Поиск существующего пользователя."""
        user = await get_user_by_phone(db, test_user.phone)

        assert user is not None
        assert user.phone == test_user.phone
        assert user.full_name == test_user.full_name

    @pytest.mark.asyncio
    async def test_get_user_by_phone_not_found(self, db):
        """A.4.2: Поиск несуществующего пользователя."""
        user = await get_user_by_phone(db, "+79990000000")
        assert user is None


class TestGetUserById:
    """Tests for get_user_by_id() function."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, db, test_user):
        """A.4.3: Поиск по ID."""
        user = await get_user_by_id(db, test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.phone == test_user.phone

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db):
        """A.4.4: Поиск по несуществующему ID."""
        user = await get_user_by_id(db, 99999)
        assert user is None


class TestCreateUser:
    """Tests for create_user() function."""

    @pytest.mark.asyncio
    async def test_create_user(self, db):
        """A.4.5: Создание нового пользователя."""
        user = await create_user(db, "Новый Пользователь", "+79991112233")

        assert user is not None
        assert user.id is not None
        assert user.full_name == "Новый Пользователь"
        assert user.phone == "+79991112233"
        assert user.is_verified is False
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_phone(self, db, test_user):
        """A.4.6: Создание с дубликатом телефона."""
        # First user already exists from fixture
        # Try to create another with same phone
        with pytest.raises(IntegrityError):
            await create_user(db, "Другой Пользователь", test_user.phone)
            await db.commit()


class TestUpdateUser:
    """Tests for update_user() function."""

    @pytest.mark.asyncio
    async def test_update_user(self, db, test_user):
        """A.4.7: Обновление имени."""
        user = await update_user(db, test_user, {"full_name": "Обновлённый"})

        assert user is not None
        assert user.full_name == "Обновлённый"
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_update_user_verify(self, db, test_user_unverified):
        """A.4.8: Верификация пользователя."""
        user = await update_user(db, test_user_unverified, {"is_verified": True})

        assert user is not None
        assert user.is_verified is True


class TestGetAllUsers:
    """Tests for get_all_users() function."""

    @pytest.mark.asyncio
    async def test_get_all_users(self, db, many_users):
        """A.4.9: Получение всех пользователей."""
        # get_all_users has default limit=50, need to specify limit=100
        users = await get_all_users(db, limit=100)

        assert len(users) == 100

    @pytest.mark.asyncio
    async def test_get_all_users_pagination(self, db, many_users):
        """Пагинация списка пользователей."""
        users = await get_all_users(db, offset=50, limit=25)

        assert len(users) == 25
        # Users are ordered by created_at desc (newest first)
        # User 100 was created last (newest), User 1 was created first (oldest)
        # So offset=50, limit=25 should return users 50-26 (in reverse order)
        assert users[0].full_name == "User 50"

    @pytest.mark.asyncio
    async def test_get_all_users_empty(self, db):
        """Получение из пустой базы."""
        users = await get_all_users(db)

        assert len(users) == 0


class TestCountUsers:
    """Tests for count_users() function."""

    @pytest.mark.asyncio
    async def test_count_users(self, db, many_users):
        """A.4.10: Подсчёт пользователей."""
        count = await count_users(db)

        assert count == 100

    @pytest.mark.asyncio
    async def test_count_users_empty(self, db):
        """Подсчёт в пустой базе."""
        count = await count_users(db)

        assert count == 0


class TestDeleteUser:
    """Tests for delete_user() function."""

    @pytest.mark.asyncio
    async def test_delete_user(self, db, test_user):
        """A.4.11: Удаление пользователя."""
        result = await delete_user(db, test_user)

        assert result is True

        # Verify user is deleted
        result = await db.execute(select(User).where(User.id == test_user.id))
        user = result.scalar_one_or_none()
        assert user is None

    @pytest.mark.asyncio
    async def test_delete_user_cascades_sessions(self, db, test_user, test_session):
        """Каскадное удаление сессий."""
        # Verify session exists before delete
        result = await db.execute(select(func.count()).select_from(Session))
        session_count_before = result.scalar()
        assert session_count_before == 1
        
        result = await delete_user(db, test_user)
        assert result is True
        
        # Verify session is also deleted (cascade)
        result = await db.execute(select(func.count()).select_from(Session))
        session_count_after = result.scalar()
        assert session_count_after == 0


class TestVerifyUser:
    """Tests for verify_user() function."""

    @pytest.mark.asyncio
    async def test_verify_user(self, db, test_user_unverified):
        """A.4.12: Верификация пользователя."""
        user = await verify_user(db, test_user_unverified)

        assert user is not None
        assert user.is_verified is True


class TestSetSmsCode:
    """Tests for set_sms_code() function."""

    @pytest.mark.asyncio
    async def test_set_sms_code(self, db, test_user):
        """A.4.13: Установка SMS кода."""
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        user = await set_sms_code(db, test_user, "1234", expires_at)

        assert user is not None
        assert user.sms_code == "1234"
        assert user.sms_code_expires_at is not None


class TestClearSmsCode:
    """Tests for clear_sms_code() function."""

    @pytest.mark.asyncio
    async def test_clear_sms_code(self, db, test_user):
        """A.4.14: Очистка SMS кода."""
        # First set a code
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        await set_sms_code(db, test_user, "1234", expires_at)
        
        # Then clear it
        user = await clear_sms_code(db, test_user)

        assert user is not None
        assert user.sms_code is None
        assert user.sms_code_expires_at is None
