# Check Call Implementation Guide

## Обзор

Добавлен новый метод авторизации «Звонок от пользователя» (Check Call), при котором пользователь сам совершает звонок на указанный номер для подтверждения.

## Изменения в базе данных

### Новые поля в таблице `users`:

1. **sms_check_id** (String, nullable)
   - Хранит идентификатор проверки от SMS.ru
   - Используется только для метода check_call

2. **is_privacy_accepted** (Boolean, default=False)
   - Флаг принятия политики конфиденциальности
   - Для будущего использования

3. **is_subscribed** (Boolean, default=False)
   - Флаг подписки на рассылку
   - Для будущего использования

### Миграция базы данных

```bash
python scripts/migrate_add_check_call_fields.py
```

**Важно:** Миграция безопасна для существующих данных:
- Все новые поля имеют значения по умолчанию или nullable
- Существующие записи не изменяются
- Потерь данных не происходит

## Конфигурация

В файле `.env` установите:

```env
AUTH_METHOD="check_call"  # sms | call | check_call
```

## Архитектура

### Backend компоненты

#### 1. Сервис Check Call (`app/services/check_call_service.py`)

```python
# Инициализация проверки
success, check_id, call_phone, message = await initiate_check_call(phone)

# Проверка статуса (опционально, для polling)
success, status, message = await verify_check_call_status(check_id)
```

#### 2. Диспетчер авторизации (`app/services/auth_dispatcher.py`)

Автоматически выбирает метод авторизации на основе `AUTH_METHOD`:
- `"sms"` — отправка SMS с кодом
- `"call"` — входящий звонок с кодом
- `"check_call"` — исходящий звонок от пользователя

#### 3. API Endpoints (`app/api/routers.py`)

**POST `/api/send-sms`**
- Для check_call: инициирует проверку, сохраняет `check_id` в `sms_check_id`

**POST `/api/auth/webhook/sms-ru`**
- Webhook endpoint для получения уведомлений от SMS.ru
- Автоматически помечает пользователя как `is_verified=True`

**GET `/api/auth/check-call-status?phone=+7...`**
- Polling endpoint для фронтенда
- Возвращает статус: `pending`, `verified`, `expired`

### Frontend компоненты

#### Страница верификации (`templates/verify.html`)

Для режима `check_call`:
- Скрывается поле ввода 4-значного кода
- Показывается кнопка «Позвонить для подтверждения»
- После нажатия кнопки запускается polling (каждые 2 сек)
- При успешной верификации — автоматический редирект на страницу карты

## Логика работы

### Этап 1: Инициализация

1. Пользователь вводит номер телефона на странице регистрации
2. Сервер делает запрос к SMS.ru: `GET /callcheck/add`
3. В ответ получает `check_id` и `call_phone`
4. Сохраняет `check_id` в поле `sms_check_id`
5. Показывает пользователю кнопку для звонка

### Этап 2: Верификация через Webhook

1. Пользователь нажимает кнопку → открывается телефонное приложение
2. Пользователь совершает звонок (бесплатный, сбрасывается автоматически)
3. SMS.ru отправляет webhook на `/api/auth/webhook/sms-ru`
4. Сервер находит пользователя по `check_id`
5. Устанавливает `is_verified=True`, очищает `sms_check_id`

### Этап 3: Ожидание на фронтенде

1. Фронтенд опрашивает `/api/auth/check-call-status` каждые 2 секунды
2. При получении `verified: true` — редирект на `/card/{phone}`
3. При `status: expired` — показ кнопки повторной попытки

## Настройка Webhook в SMS.ru

В личном кабинете SMS.ru:
1. Перейти в раздел «Настройки Callback»
2. Указать URL: `https://your-domain.com/api/auth/webhook/sms-ru`
3. Сохранить настройки

## Тестирование

### Режим тестирования

При `SMS_TEST_MODE=True`:
- `initiate_check_call` возвращает тестовый `check_id`
- `verify_check_call_status` симулирует успешную верификацию
- Реальные звонки не совершаются

### Проверка локально

```bash
# 1. Запустить миграцию
python scripts/migrate_add_check_call_fields.py

# 2. Установить режим тестирования
export AUTH_METHOD="check_call"
export SMS_TEST_MODE="True"

# 3. Запустить сервер
uvicorn app.main:app --reload

# 4. Открыть http://localhost:8000
# 5. Зарегистрироваться → проверить верификацию
```

## Совместимость

- ✅ Существующие пользователи работают без изменений
- ✅ Методы `sms` и `call` продолжают работать
- ✅ Переключение между методами через `AUTH_METHOD`
- ✅ Безопасное расширение БД (backward compatible)

## Структура файлов

```
app/
├── models.py                    # +3 новых поля в User
├── services/
│   ├── check_call_service.py    # Новый сервис
│   └── auth_dispatcher.py       # Обновлён для check_call
├── api/
│   └── routers.py               # +webhook, +polling endpoints
templates/
└── verify.html                  # Обновлён для check_call UI
scripts/
└── migrate_add_check_call_fields.py  # Скрипт миграции
docs/
└── CHECK_CALL_IMPLEMENTATION.md # Этот файл
```

## Ответы на частые вопросы

**Q: Что если webhook не придёт?**
A: Фронтенд продолжает polling. Можно также вручную проверить статус через API SMS.ru.

**Q: Сколько времени есть на звонок?**
A: 5 минут (как и для SMS кода).

**Q: Можно ли переключать AUTH_METHOD на лету?**
A: Да, все методы используют общую структуру и совместимы.

**Q: Нужно ли запускать миграцию обязательно?**
A: Приложение запустится и без миграции, но check_call не будет работать корректно.