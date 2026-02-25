## План доработок: Механизм сессий и авто-вход (Update Plan v1.0)

### Проблема

В текущей реализации после перезагрузки страницы или повторного открытия приложения пользователь попадает на страницу регистрации, даже если уже прошёл верификацию. Необходимо реализовать механизм сессий для запоминания пользователя.

---

### Этап U1: Сервис сессий (Backend)

#### U1.1. Создание сервиса сессий
* **Цель:** Реализовать генерацию, хранение и проверку сессионных токенов.
* **Файл:** `app/services/session_service.py`
* **Функции:**
  - `create_session(db, user_id)` → `session_token` (генерация токена)
  - `get_session_by_token(db, token)` → `Session | None` (проверка токена)
  - `delete_session(db, token)` → `bool` (выход из системы)
  - `cleanup_expired_sessions(db)` → `int` (удаление просроченных сессий)
* **Логика:**
  - Токен: UUID v4 или secrets.token_urlsafe(32)
  - Срок жизни: 30 дней
  - Хранение: отдельная таблица `sessions` (user_id, token, expires_at, created_at)

#### U1.2. Обновление модели User
* **Цель:** Добавить связь с сессиями.
* **Файл:** `app/models.py`
* **Изменения:**
  - Добавить модель `Session` (id, user_id, token, expires_at, created_at)
  - Добавить relationship в модель `User`

#### U1.3. Обновление API: вход по телефону
* **Цель:** Реализовать упрощённый вход для зарегистрированных пользователей.
* **Файл:** `app/api/routers.py`
* **Новые эндпоинты:**
  - `POST /api/login` → вход по телефону (без SMS для verified)
  - `POST /api/logout` → выход из системы (удаление сессии)
  - `GET /api/me` → получение текущего пользователя (проверка сессии)

#### U1.4. Middleware для проверки сессии
* **Цель:** Автоматическая проверка сессии для всех запросов.
* **Файл:** `app/middleware/auth.py`
* **Логика:**
  - Извлекать `session_token` из cookie
  - Проверять валидность сессии в БД
  - Добавлять `current_user` в `request.state`
  - Пропускать запрос, если сессия невалидна (обработка в роутерах)

---

### Этап U2: Обновление Frontend (Client)

#### U2.1. Обновление страницы регистрации (index.html)
* **Цель:** Проверка сессии при загрузке, упрощённый вход.
* **Файл:** `templates/index.html`
* **Изменения:**
  - При загрузке: проверка `localStorage.getItem('session_token')`
  - Если сессия есть → запрос `/api/me` → редирект на `/card/{phone}`
  - Если сессии нет → показать форму
  - После ввода телефона: проверка в БД
    - Новый пользователь → регистрация → SMS
    - Зарегистрированный verified → вход без SMS → редирект на карту
    - Зарегистрированный not verified → SMS → верификация

#### U2.2. Обновление страницы верификации (verify.html)
* **Цель:** Сохранение сессии после успешной верификации.
* **Файл:** `templates/verify.html`
* **Изменения:**
  - После успешного `/api/verify` → запрос `/api/login` → получение токена
  - Сохранение токена в `localStorage.setItem('session_token', token)`
  - Сохранение телефона в `localStorage.setItem('phone', phone)`
  - Редирект на `/card/{phone}`

#### U2.3. Обновление страницы карты (card.html)
* **Цель:** Проверка сессии, возможность выхода.
* **Файл:** `templates/card.html`
* **Изменения:**
  - При загрузке: проверка сессии через `/api/me`
  - Если сессия невалидна → редирект на `/`
  - Добавить кнопку "Выйти" → `/api/logout` + очистка localStorage

#### U2.4. Базовый шаблон (base.html)
* **Цель:** Централизованная проверка сессии.
* **Файл:** `templates/base.html`
* **Изменения:**
  - Добавить скрипт проверки сессии при загрузке любой страницы
  - Глобальная функция `checkSession()` для всех страниц

---

### Этап U3: Три сценария работы (Implementation)

#### Сценарий 1: Новый клиент (первый вход)
```
GET / → index.html (форма регистрации)
POST /api/register → создание User (is_verified=False)
POST /api/send-sms → отправка кода
GET /verify?phone=... → verify.html (ввод кода)
POST /api/verify → проверка кода, установка is_verified=True
POST /api/login → создание сессии, возврат токена
localStorage.setItem('session_token', token)
Redirect → /card/{phone}
```

#### Сценарий 2: Зарегистрированный и верифицированный (повторный вход)
```
GET / → checkSession() в base.html
localStorage.getItem('session_token') → есть
GET /api/me → валидная сессия, is_verified=True
Redirect → /card/{phone} (без форм, без SMS)
```

#### Сценарий 3: Зарегистрированный, но НЕ верифицированный
```
GET / → checkSession() в base.html
localStorage.getItem('session_token') → нет или истёк
GET / → index.html (форма входа по телефону)
POST /api/login (только телефон) → проверка в БД
is_verified=False → POST /api/send-sms
GET /verify?phone=... → verify.html (ввод кода)
POST /api/verify → проверка кода, is_verified=True
POST /api/login → создание сессии
localStorage.setItem('session_token', token)
Redirect → /card/{phone}
```

---

### Этап U4: Безопасность и оптимизация

#### U4.1. HttpOnly Cookie (опционально)
* **Файл:** `app/api/routers.py`
* **Логика:**
  - Установка cookie: `response.set_cookie(key="session_token", value=token, httponly=True, secure=True, max_age=2592000)`
  - Чтение cookie в middleware вместо localStorage

#### U4.2. Rate Limiting для /api/send-sms
* **Файл:** `app/middleware/rate_limit.py`
* **Логика:**
  - Максимум 3 SMS в час на один номер
  - Блокировка по IP или phone

#### U4.3. HTTPS для продакшена
* **Файл:** `nginx.conf` или инструкция для Selectel
* **Логика:**
  - SSL-сертификат Let's Encrypt
  - Редирект HTTP → HTTPS
  - Secure cookie только для HTTPS

---

### Зависимости между этапами доработок

```
U1 (Session Service) → U2 (Frontend) → U3 (Сценарии) → U4 (Безопасность)
       ↓                      ↓
   Модель Session         Middleware auth
```

---

### Приоритет реализации

| Приоритет | Этап | Описание |
|-----------|------|----------|
| 🔴 Высокий | U1.1–U1.3 | Сервис сессий, модель, API |
| 🔴 Высокий | U2.1–U2.3 | Обновление frontend (localStorage) |
| 🟡 Средний | U3 | Интеграция сценариев |
| 🟢 Низкий | U4 | Безопасность (cookie, rate limit, HTTPS) |

---

### Оценка времени

| Этап | Время |
|------|-------|
| U1 (Backend) | 2–3 часа |
| U2 (Frontend) | 2–3 часа |
| U3 (Интеграция) | 1–2 часа |
| U4 (Безопасность) | 2–4 часа |
| **Итого** | **7–12 часов** |

---

## Итоговая таблица статусов

| Компонент | Статус | Файлы |
|-----------|--------|-------|
| Инфраструктура | ✅ | requirements.txt, .env, app/ |
| База данных | ✅ | models.py, database.py |
| API роутеры | ✅ | routers.py |
| Схемы Pydantic | ✅ | schemas.py |
| CRUD сервис | ✅ | services/crud.py |
| SMS сервис | ✅ | services/sms_service.py |
| Phone сервис | ✅ | services/phone_service.py |
| Templates | ✅ | base.html, index.html, verify.html, card.html, admin.html |
| PWA Manifest | ✅ | manifest.json, icons |
| Админка | ✅ | admin.html, /admin/export |
| **Сессии** | **❌** | **Требуется U1–U3** |
| Деплой | ⏳ | Docker, Nginx, SSL |
| Тесты | ⏳ | tests/ |
