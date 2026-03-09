"""
Unit tests for phone_service.py

Tests phone number validation and normalization functions.
"""

import pytest
from app.services.phone_service import (
    normalize_phone,
    validate_phone,
    format_phone_display,
    extract_phone_code
)


class TestNormalizePhone:
    """Tests for normalize_phone() function."""

    def test_normalize_phone_plus7(self):
        """A.1.1: Нормализация +7 (999) 123-45-67."""
        result = normalize_phone("+7 (999) 123-45-67")
        assert result == "+79991234567"

    def test_normalize_phone_7(self):
        """A.1.2: Нормализация 79991234567."""
        result = normalize_phone("79991234567")
        assert result == "+79991234567"

    def test_normalize_phone_8(self):
        """A.1.3: Нормализация 89991234567."""
        result = normalize_phone("89991234567")
        assert result == "+79991234567"

    def test_normalize_phone_formatted(self):
        """A.1.4: Нормализация +7 (999) 123-45-67."""
        result = normalize_phone("+7 (999) 123-45-67")
        assert result == "+79991234567"

    def test_normalize_phone_plain_plus7(self):
        """Нормализация +79991234567 без форматирования."""
        result = normalize_phone("+79991234567")
        assert result == "+79991234567"

    def test_normalize_phone_invalid(self):
        """A.1.5: Неверный формат 12345."""
        with pytest.raises(ValueError) as exc_info:
            normalize_phone("12345")
        assert "must start with +7, 7, or 8" in str(exc_info.value)

    def test_normalize_phone_short(self):
        """A.1.6: Короткий номер +7123."""
        with pytest.raises(ValueError) as exc_info:
            normalize_phone("+7123")
        assert "must have 11 digits" in str(exc_info.value)

    def test_normalize_phone_long(self):
        """A.1.7: Длинный номер +7999123456789."""
        with pytest.raises(ValueError) as exc_info:
            normalize_phone("+7999123456789")
        assert "must have 11 digits" in str(exc_info.value)

    def test_normalize_phone_plus8(self):
        """Нормализация +8 (замена на +7)."""
        result = normalize_phone("+89991234567")
        assert result == "+79991234567"

    def test_normalize_phone_with_spaces(self):
        """Нормализация номера с пробелами."""
        result = normalize_phone("+7 999 123 45 67")
        assert result == "+79991234567"


class TestValidatePhone:
    """Tests for validate_phone() function."""

    def test_validate_phone_valid(self):
        """A.1.8: Валидный номер +79991234567."""
        result = validate_phone("+79991234567")
        assert result is True

    def test_validate_phone_formatted(self):
        """Валидный номер в формате +7 (XXX) XXX-XX-XX."""
        result = validate_phone("+7 (999) 123-45-67")
        assert result is True

    def test_validate_phone_8(self):
        """Валидный номер с 8."""
        result = validate_phone("89991234567")
        assert result is True

    def test_validate_phone_invalid(self):
        """A.1.9: Невалидный номер +19991234567."""
        result = validate_phone("+19991234567")
        assert result is False

    def test_validate_phone_short(self):
        """Слишком короткий номер."""
        result = validate_phone("+7999123")
        assert result is False

    def test_validate_phone_letters(self):
        """Номер с буквами - буквы игнорируются при нормализации."""
        # Note: validate_phone strips non-digit chars, so this returns True
        # because "+79991234567abc" becomes "+79991234567" after normalization
        result = validate_phone("+79991234567abc")
        assert result is True  # Letters are stripped during normalization


class TestFormatPhoneDisplay:
    """Tests for format_phone_display() function."""

    def test_format_phone_display(self):
        """A.1.10: Форматирование для отображения."""
        result = format_phone_display("+79991234567")
        assert result == "+7 (999) 123-45-67"

    def test_format_phone_display_without_plus(self):
        """Форматирование номера без +."""
        result = format_phone_display("79991234567")
        assert result == "+7 (999) 123-45-67"

    def test_format_phone_display_8(self):
        """Форматирование номера с 8."""
        result = format_phone_display("89991234567")
        assert result == "+7 (999) 123-45-67"


class TestExtractPhoneCode:
    """Tests for extract_phone_code() function."""

    def test_extract_phone_code(self):
        """Извлечение кода оператора."""
        result = extract_phone_code("+79991234567")
        assert result == "999"

    def test_extract_phone_code_different_operator(self):
        """Извлечение кода другого оператора."""
        result = extract_phone_code("+79261234567")
        assert result == "926"

    def test_extract_phone_code_without_plus(self):
        """Извлечение кода из номера без +."""
        result = extract_phone_code("79991234567")
        assert result == "999"
