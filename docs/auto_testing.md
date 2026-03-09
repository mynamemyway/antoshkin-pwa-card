# План автоматического тестирования Antoshkin Loyalty Card

## 📋 Обзор

Этот документ описывает стратегию автоматического тестирования PWA-приложения карты лояльности.

---

## 🧪 Уровни тестирования

### 1. Unit-тесты (модульные)
- Тестирование отдельных функций и сервисов
- Изолированная проверка бизнес-логики
- Мокирование внешних зависимостей (БД, SMS API)

### 2. Integration-тесты (интеграционные)
- Тестирование взаимодействия между модулями
- Тестирование API эндпоинтов
- Тестирование работы с базой данных

### 3. E2E-тесты (end-to-end)
- Полные сценарии использования
- Тестирование через браузер (Playwright/Selenium)
- Проверка пользовательских сценариев

---

## 📝 Список тестов

### A. Unit-тесты (сервисный слой)

#### A.1. `test_phone_service.py` — Валидация телефонов

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| A.1.1 | `test_normalize_phone_plus7` | Нормализация `+7 (999) 123-45-67` | `+79991234567` |
| A.1.2 | `test_normalize_phone_7` | Нормализация `79991234567` | `+79991234567` |
| A.1.3 | `test_normalize_phone_8` | Нормализация `89991234567` | `+79991234567` |
| A.1.4 | `test_normalize_phone_formatted` | Нормализация `+7 (999) 123-45-67` | `+79991234567` |
| A.1.5 | `test_normalize_phone_invalid` | Неверный формат `12345` | `ValueError` |
| A.1.6 | `test_normalize_phone_short` | Короткий номер `+7123` | `ValueError` |
| A.1.7 | `test_normalize_phone_long` | Длинный номер `+7999123456789` | `ValueError` |
| A.1.8 | `test_validate_phone_valid` | Валидный номер `+79991234567` | `True` |
| A.1.9 | `test_validate_phone_invalid` | Невалидный номер `+19991234567` | `False` |
| A.1.10 | `test_format_phone_display` | Форматирование для отображения | `+7 (999) 123-45-67` |

---

#### A.2. `test_sms_service.py` — SMS-верификация

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| A.2.1 | `test_generate_sms_code_test_mode` | Генерация кода в тестовом режиме | `"0000"` |
| A.2.2 | `test_generate_sms_code_prod_mode` | Генерация кода в боевом режиме | 4-значное число |
| A.2.3 | `test_generate_sms_code_format` | Формат кода | Строка из 4 цифр |
| A.2.4 | `test_verify_sms_code_valid` | Верификация верным кодом | `(True, "Verified")` |
| A.2.5 | `test_verify_sms_code_invalid` | Верификация неверным кодом | `(False, "Неверный код")` |
| A.2.6 | `test_verify_sms_code_expired` | Верификация просроченным кодом | `(False, "Срок действия кода истёк")` |
| A.2.7 | `test_verify_sms_code_already_verified` | Верификация верифицированного | `(True, "Already verified")` |
| A.2.8 | `test_verify_sms_code_no_code` | Верификация без отправки кода | `(False, "Код не был отправлен")` |
| A.2.9 | `test_set_user_sms_code` | Установка SMS-кода | Код сохранён, expires_at = +5 мин |
| A.2.10 | `test_resend_sms_code` | Повторная отправка кода | Новый код сохранён |
| A.2.11 | `test_resend_sms_code_verified` | Повторная отправка верифицированному | `(False, "", "User already verified")` |

---

#### A.3. `test_session_service.py` — Управление сессиями

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| A.3.1 | `test_create_session` | Создание сессии | Токен создан, expires_at = +30 дней |
| A.3.2 | `test_create_session_custom_expiry` | Создание сессии с кастомным сроком | expires_at = указанная дата |
| A.3.3 | `test_get_session_by_token_valid` | Получение валидной сессии | Session объект |
| A.3.4 | `test_get_session_by_token_invalid` | Получение несуществующей сессии | `None` |
| A.3.5 | `test_delete_session` | Удаление сессии | `True`, сессия удалена из БД |
| A.3.6 | `test_delete_session_not_found` | Удаление несуществующей сессии | `False` |
| A.3.7 | `test_session_is_valid` | Проверка валидности сессии | `True` / `False` |
| A.3.8 | `test_cleanup_expired_sessions` | Очистка просроченных сессий | Количество удалённых сессий |
| A.3.9 | `test_delete_all_user_sessions` | Удаление всех сессий пользователя | Количество удалённых сессий |

---

#### A.4. `test_crud.py` — CRUD операции

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| A.4.1 | `test_get_user_by_phone_found` | Поиск существующего пользователя | User объект |
| A.4.2 | `test_get_user_by_phone_not_found` | Поиск несуществующего пользователя | `None` |
| A.4.3 | `test_get_user_by_id_found` | Поиск по ID | User объект |
| A.4.4 | `test_get_user_by_id_not_found` | Поиск по несуществующему ID | `None` |
| A.4.5 | `test_create_user` | Создание нового пользователя | User с id, created_at |
| A.4.6 | `test_create_user_duplicate_phone` | Создание с дубликатом телефона | `IntegrityError` |
| A.4.7 | `test_update_user` | Обновление данных пользователя | Данные обновлены |
| A.4.8 | `test_get_all_users` | Получение списка пользователей | Список User, отсортированный по created_at |
| A.4.9 | `test_get_all_users_pagination` | Пагинация списка | Ограниченное количество (limit, offset) |
| A.4.10 | `test_count_users` | Подсчёт количества пользователей | Число пользователей |
| A.4.11 | `test_delete_user` | Удаление пользователя | `True`, пользователь удалён |
| A.4.12 | `test_verify_user` | Верификация пользователя | `is_verified = True`, код очищен |
| A.4.13 | `test_set_sms_code` | Установка SMS-кода | Код и expires_at сохранены |
| A.4.14 | `test_clear_sms_code` | Очистка SMS-кода | Код и expires_at = None |

---

### B. Integration-тесты (API эндпоинты)

#### B.1. `test_api_register.py` — Регистрация

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| B.1.1 | `test_register_new_user` | Регистрация нового пользователя | 200 OK, UserOut с данными |
| B.1.2 | `test_register_existing_user` | Регистрация существующего пользователя | 200 OK, данные существующего |
| B.1.3 | `test_register_invalid_phone` | Регистрация с неверным телефоном | 422 Validation Error |
| B.1.4 | `test_register_missing_name` | Регистрация без имени | 422 Validation Error |
| B.1.5 | `test_register_missing_phone` | Регистрация без телефона | 422 Validation Error |
| B.1.6 | `test_register_phone_format_plus7` | Телефон в формате `+7XXXXXXXXXX` | Успешная регистрация |
| B.1.7 | `test_register_phone_format_8` | Телефон в формате `8XXXXXXXXXX` | Успешная регистрация, нормализация |
| B.1.8 | `test_register_phone_format_7` | Телефон в формате `7XXXXXXXXXX` | Успешная регистрация, нормализация |
| B.1.9 | `test_register_duplicate_phone_case_insensitive` | Дубликат телефона (разный регистр) | Возврат существующего пользователя |

---

#### B.2. `test_api_send_sms.py` — Отправка SMS

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| B.2.1 | `test_send_sms_success` | Успешная отправка SMS | 200 OK, `{"sent": true}` |
| B.2.2 | `test_send_sms_user_not_found` | Отправка несуществующему пользователю | 404 Not Found |
| B.2.3 | `test_send_sms_test_mode` | Отправка в тестовом режиме | 200 OK, код "0000" |
| B.2.4 | `test_send_sms_verified_user` | Отправка верифицированному пользователю | 200 OK (для повторного входа) |
| B.2.5 | `test_send_sms_code_saved` | Проверка сохранения кода в БД | sms_code сохранён, expires_at = +5 мин |
| B.2.6 | `test_send_sms_invalid_phone` | Отправка с неверным телефоном | 422 Validation Error |

---

#### B.3. `test_api_verify.py` — Верификация кода

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| B.3.1 | `test_verify_code_success` | Успешная верификация | 200 OK, `{"verified": true}`, cookie установлен |
| B.3.2 | `test_verify_code_invalid` | Неверный код | 400 Bad Request |
| B.3.3 | `test_verify_code_expired` | Просроченный код | 400 Bad Request |
| B.3.4 | `test_verify_code_not_found` | Верификация несуществующего пользователя | 404 Not Found |
| B.3.5 | `test_verify_code_no_code_sent` | Верификация без отправки кода | 400 Bad Request |
| B.3.6 | `test_verify_code_sets_cookie` | Проверка установки cookie | HttpOnly cookie с токеном |
| B.3.7 | `test_verify_code_marks_user_verified` | Проверка статуса верификации | `is_verified = True` |
| B.3.8 | `test_verify_code_clears_sms_code` | Проверка очистки кода после верификации | sms_code = None |
| B.3.9 | `test_verify_already_verified_user` | Верификация верифицированного пользователя | 200 OK (повторный вход) |

---

#### B.4. `test_api_session.py` — Сессии

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| B.4.1 | `test_login_success` | Успешный вход по телефону | 200 OK, SMS отправлена |
| B.4.2 | `test_login_user_not_found` | Вход несуществующего пользователя | 404 Not Found |
| B.4.3 | `test_logout_success` | Успешный выход | 200 OK, cookie удалён, сессия удалена из БД |
| B.4.4 | `test_logout_no_cookie` | Выход без cookie | 200 OK |
| B.4.5 | `test_get_current_user_authenticated` | Получение текущего пользователя (авторизован) | 200 OK, UserOut |
| B.4.6 | `test_get_current_user_unauthenticated` | Получение текущего пользователя (не авторизован) | 401 Unauthorized |
| B.4.7 | `test_get_current_user_expired_session` | Сессия с истёкшим сроком | 401 Unauthorized |
| B.4.8 | `test_get_current_user_invalid_token` | Неверный токен сессии | 401 Unauthorized |

---

#### B.5. `test_api_admin.py` — Админ-панель

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| B.5.1 | `test_admin_panel_success` | Доступ к админ-панели | 200 OK, HTML с таблицей |
| B.5.2 | `test_admin_panel_pagination` | Пагинация в админ-панели | 50 пользователей на странице |
| B.5.3 | `test_admin_panel_page_2` | Доступ ко второй странице | 200 OK, пользователи 51-100 |
| B.5.4 | `test_admin_panel_search_found` | Поиск по телефону (найдено) | 200 OK, отфильтрованные пользователи |
| B.5.5 | `test_admin_panel_search_not_found` | Поиск по телефону (не найдено) | 200 OK, пустая таблица |
| B.5.6 | `test_admin_panel_search_partial` | Поиск по части номера | 200 OK, все совпадения |
| B.5.7 | `test_admin_panel_verified_count` | Подсчёт верифицированных | Корректное число всех верифицированных |
| B.5.8 | `test_admin_export_csv` | Экспорт в CSV | 200 OK, CSV файл с заголовком |
| B.5.9 | `test_admin_export_csv_content` | Проверка содержимого CSV | Корректные данные пользователей |

---

#### B.6. `test_api_card.py` — Карта пользователя

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| B.6.1 | `test_card_page_success` | Доступ к карте верифицированного | 200 OK, HTML с QR-кодом |
| B.6.2 | `test_card_page_not_verified` | Доступ к карте неверифицированного | Redirect на /verify |
| B.6.3 | `test_card_page_user_not_found` | Доступ к карте несуществующего | 404 Not Found |
| B.6.4 | `test_card_page_qr_data` | Проверка данных QR-кода | JSON с user_id и phone |

---

#### B.7. `test_api_pages.py` — Страницы

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| B.7.1 | `test_root_page` | Доступ к главной странице | 200 OK, HTML регистрации |
| B.7.2 | `test_verify_page` | Доступ к странице верификации | 200 OK, HTML с полем кода |
| B.7.3 | `test_splash_page` | Доступ к splash screen | 200 OK, HTML splash |
| B.7.4 | `test_health_check` | Проверка health endpoint | 200 OK, `{"status": "ok"}` |

---

### C. Integration-тесты (Middleware)

#### C.1. `test_auth_middleware.py` — Аутентификация

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| C.1.1 | `test_middleware_valid_session` | Middleware с валидной сессией | `request.state.current_user` установлен |
| C.1.2 | `test_middleware_no_cookie` | Middleware без cookie | `request.state.current_user = None` |
| C.1.3 | `test_middleware_invalid_token` | Middleware с неверным токеном | `request.state.current_user = None` |
| C.1.4 | `test_middleware_expired_session` | Middleware с просроченной сессией | `request.state.current_user = None` |
| C.1.5 | `test_middleware_is_authenticated` | Middleware устанавливает флаг | `request.state.is_authenticated = True` |

---

### D. E2E-тесты (пользовательские сценарии)

#### D.1. `test_e2e_registration.py` — Регистрация нового пользователя

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| D.1.1 | `test_e2e_new_user_registration` | Полный цикл регистрации нового пользователя | Успешная регистрация, верификация, карта |
| D.1.2 | `test_e2e_registration_invalid_phone` | Регистрация с неверным телефоном | Ошибка валидации на форме |
| D.1.3 | `test_e2e_registration_sms_not_received` | SMS не получена (таймаут) | Возможность запросить код повторно |
| D.1.4 | `test_e2e_registration_wrong_code` | Ввод неверного кода | Ошибка "Неверный код" |
| D.1.5 | `test_e2e_registration_expired_code` | Ввод кода после истечения срока | Ошибка "Срок действия кода истёк" |

---

#### D.2. `test_e2e_login.py` — Повторный вход

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| D.2.1 | `test_e2e_login_with_valid_session` | Вход с валидной сессией (cookie) | Автоматический редирект на карту |
| D.2.2 | `test_e2e_login_after_logout` | Вход после выхода | Требуется ввод SMS-кода |
| D.2.3 | `test_e2e_login_expired_session` | Вход с просроченной сессией | Требуется ввод SMS-кода |
| D.2.4 | `test_e2e_login_new_device` | Вход с нового устройства (без cookie) | Требуется ввод SMS-кода |

---

#### D.3. `test_e2e_pwa.py` — PWA функциональность

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| D.3.1 | `test_e2e_pwa_manifest` | Проверка manifest.json | 200 OK, корректный манифест |
| D.3.2 | `test_e2e_pwa_icons` | Проверка иконок | Все иконки доступны (180, 192, 512) |
| D.3.3 | `test_e2e_pwa_install_hint` | Проверка инструкции по установке | Инструкция показывается/скрывается |
| D.3.4 | `test_e2e_pwa_standalone_mode` | Проверка standalone режима | Инструкция скрыта в установленном PWA |
| D.3.5 | `test_e2e_pwa_offline` | Проверка офлайн-режима | Страницы кэшируются (если реализовано) |

---

#### D.4. `test_e2e_admin.py` — Админ-панель

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| D.4.1 | `test_e2e_admin_view_users` | Просмотр списка пользователей | Таблица с пользователями отображается |
| D.4.2 | `test_e2e_admin_search_phone` | Поиск по телефону | Таблица фильтруется мгновенно |
| D.4.3 | `test_e2e_admin_pagination` | Пагинация | Кнопки "Пред./След." работают |
| D.4.4 | `test_e2e_admin_export_csv` | Экспорт в CSV | Файл скачивается с корректными данными |
| D.4.5 | `test_e2e_admin_verified_count` | Подсчёт верифицированных | Число совпадает с БД |

---

#### D.5. `test_e2e_user_scenarios.py` — Сценарии из README

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| D.5.1 | `test_e2e_scenario_1_new_user` | Сценарий 1: Новый пользователь | Регистрация → SMS → Карта |
| D.5.2 | `test_e2e_scenario_2_repeat_login` | Сценарий 2: Повторный вход (с сессией) | Автоматический вход → Карта |
| D.5.3 | `test_e2e_scenario_3_logout_login` | Сценарий 3: Выход и повторный вход | Выход → SMS → Карта |
| D.5.4 | `test_e2e_scenario_4_pwa_install` | Сценарий 4: Установка PWA | Инструкция → Иконка на главном экране |

---

### E. Нагрузочные тесты (опционально)

#### E.1. `test_load_concurrent_registration.py` — Конкурентная регистрация

| № | Тест | Описание | Ожидаемый результат |
|---|------|----------|---------------------|
| E.1.1 | `test_load_10_concurrent_registrations` | 10 одновременных регистраций | Все успешны, нет race condition |
| E.1.2 | `test_load_50_concurrent_sms_requests` | 50 одновременных запросов SMS | Все успешны, нет блокировок |
| E.1.3 | `test_load_database_write_contention` | Конкурентная запись в БД | Нет deadlock, все транзакции завершены |

---

## 🛠 Инструменты

### Для Unit и Integration тестов:
- **pytest** — фреймворк для тестирования
- **pytest-asyncio** — поддержка асинхронных тестов
- **pytest-cov** — покрытие кода
- **httpx** — асинхронный HTTP-клиент для тестов API
- **pytest-mock** — мокирование

### Для E2E тестов:
- **Playwright** — браузерная автоматизация (быстрее Selenium)
- **pytest-playwright** — интеграция с pytest

### Для нагрузочных тестов:
- **locust** — нагрузочное тестирование
- **pytest-xdist** — параллельный запуск тестов

---

## 📁 Структура тестов

```
tests/
├── __init__.py
├── conftest.py              # Фикстуры pytest (db, client, mock SMS)
├── unit/
│   ├── __init__.py
│   ├── test_phone_service.py
│   ├── test_sms_service.py
│   ├── test_session_service.py
│   └── test_crud.py
├── integration/
│   ├── __init__.py
│   ├── test_api_register.py
│   ├── test_api_send_sms.py
│   ├── test_api_verify.py
│   ├── test_api_session.py
│   ├── test_api_admin.py
│   ├── test_api_card.py
│   ├── test_api_pages.py
│   └── test_auth_middleware.py
└── e2e/
    ├── __init__.py
    ├── test_e2e_registration.py
    ├── test_e2e_login.py
    ├── test_e2e_pwa.py
    ├── test_e2e_admin.py
    └── test_e2e_user_scenarios.py
```

---

## 🚀 Запуск тестов

### Все тесты:
```bash
pytest
```

### Unit-тесты:
```bash
pytest tests/unit/
```

### Integration-тесты:
```bash
pytest tests/integration/
```

### E2E-тесты:
```bash
pytest tests/e2e/
```

### С покрытием:
```bash
pytest --cov=app --cov-report=html
```

### В режиме verbose:
```bash
pytest -v
```

### Конкретный тест:
```bash
pytest tests/unit/test_sms_service.py::test_verify_sms_code_valid -v
```

---

## 📊 Покрытие кода

Целевое покрытие:
- **Unit-тесты:** ≥ 90%
- **Integration-тесты:** ≥ 80%
- **E2E-тесты:** ≥ 70% критических сценариев

---

## 📝 Приоритеты реализации

### Фаза 1 (критично):
1. Unit-тесты сервисов (A.1–A.4)
2. Integration-тесты API (B.1–B.4)
3. Integration-тесты middleware (C.1)

### Фаза 2 (важно):
4. Integration-тесты админки (B.5–B.7)
5. E2E-тесты регистрации и входа (D.1–D.2)

### Фаза 3 (желательно):
6. E2E-тесты PWA (D.3)
7. E2E-тесты админки (D.4)
8. E2E-тесты сценариев (D.5)

### Фаза 4 (опционально):
9. Нагрузочные тесты (E.1)

---

## 🔧 Фикстуры (conftest.py)

### Необходимые фикстуры:

| Фикстура | Описание |
|----------|----------|
| `db` | Тестовая база данных (SQLite in-memory) |
| `client` | TestClient для API запросов |
| `test_user` | Тестовый пользователь в БД |
| `test_session` | Тестовая сессия |
| `mock_sms_service` | Мок для отправки SMS |
| `auth_headers` | Заголовки с cookie для авторизации |

---

## ⚠️ Особенности тестирования

### Тестирование SMS:
- В тестах использовать `SMS_TEST_MODE=True`
- Мокать функцию `send_sms()` для изоляции
- Проверять только логику, не реальную отправку

### Тестирование сессий:
- Мокать `datetime.utcnow()` для проверки истечения срока
- Проверять установку/удаление cookie

### Тестирование БД:
- Использовать in-memory SQLite для скорости
- Очищать БД после каждого теста (rollback)

### Тестирование middleware:
- Проверять `request.state.current_user`
- Проверять `request.state.is_authenticated`

---

## 📈 Метрики качества

- Все тесты должны проходить (100% pass rate)
- Время выполнения всех тестов: ≤ 5 минут
- Время выполнения CI pipeline: ≤ 10 минут
- Покрытие кода: ≥ 80%

---

## 🔄 CI/CD интеграция

### GitHub Actions workflow:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: pip install -r requirements.txt && pip install -r requirements-test.txt
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```
35 failed, 77 passed, 825 warnings
python -m pytest