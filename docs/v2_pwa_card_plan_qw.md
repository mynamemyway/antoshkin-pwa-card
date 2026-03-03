# План деплоя: Проект "Antoshkin PWA Card"

## 0. Конфигурация

## Конфигурация сервера

**Сервер:** `91.206.14.93`  
**Пользователь:** `mynamemyway`  
**Путь к проекту:** `/home/mynamemyway/projects/antoshkin-pwa-card`  
**Домен:** `card.rassada1.ru` (требуется A-запись)

---

## Этап 1: Подготовка (Локально)

### 1.1. Конфиг окружения

Скопировать файл `.env` в корень репозитория на сервере. **Важно:** `DATABASE_URL` должен указывать на путь внутри контейнера.

```bash
DATABASE_URL=sqlite:///./data/loyalty.db
SMS_API_KEY=48395181-0488-1E87-4DF1-62242141953E
SMS_TEST_MODE=false
DEBUG=false
```

### 1.2. Docker-слой

**Dockerfile:** Используем `python:3.12-slim`.
**docker-compose.yml:** Главные правки здесь — прямой проброс сертификатов и автозапуск.

```yaml
services:
  app:
    build: .
    restart: always
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro # Прямой доступ к сертификатам системы
    restart: always
    depends_on:
      - app

```

---

## Этап 2: Настройка Reverse Proxy (Nginx)

### 2.1. Создание `nginx.conf`

Настраиваем пересылку трафика на наше FastAPI приложение и указываем пути к SSL.

```nginx
server {
    listen 80;
    server_name card.rassada1.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name card.rassada1.ru;

    ssl_certificate /etc/letsencrypt/live/card.rassada1.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/card.rassada1.ru/privkey.pem;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

```

---

## Этап 3: Подготовка сервера

### 3.1. Инфраструктура и DNS

1. **DNS:** Убедись, что А-запись `card.rassada1.ru` → `91.206.14.93` активна (`ping card.rassada1.ru`).
2. **Firewall:** Открываем двери для веба.
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

```

3. **Папки:**
```bash
mkdir -p /home/mynamemyway/projects/antoshkin-pwa-card/data

```

---

## Этап 4: Магия SSL (Certbot)

**Критически важно:** Делаем это ДО запуска Docker, так как нам нужен свободный 80 порт.

1. **Установка:** `sudo apt install certbot -y`
2. **Получение:**
```bash
sudo certbot certonly --standalone \
  -d card.rassada1.ru \
  --email твой_email@mail.com \
  --agree-tos --non-interactive

```

*Теперь сертификаты лежат в `/etc/letsencrypt/live/`, и Docker увидит их через проброшенный volume.*

---

## Этап 5: Запуск и Автоматизация

### 5.1. Старт приложения

```bash
cd /home/mynamemyway/projects/antoshkin-pwa-card
docker compose up -d --build

```

### 5.2. Авто-продление SSL (Бессмертный режим)

Нам нужно, чтобы Certbot умел останавливать Nginx в докере на время проверки и запускать обратно. Настрой это одной командой:

```bash
sudo certbot renew --dry-run --pre-hook "docker compose -f /home/mynamemyway/projects/antoshkin-pwa-card/docker-compose.yml stop nginx" --post-hook "docker compose -f /home/mynamemyway/projects/antoshkin-pwa-card/docker-compose.yml start nginx"

```

*Если dry-run прошел успешно, всё будет обновляться автоматически системным таймером.*

---

## Этап 6: Тестирование (Checklist)

1. [ ] **HTTPS:** Замок в браузере горит зеленым.
2. [ ] **Redirect:** При вводе `http://` перекидывает на `https://`.
3. [ ] **PWA:** В меню Chrome (на Android) появился пункт "Установить приложение".
4. [ ] **SMS:** Код пришел на телефон (не в логах, а в реальности).
5. [ ] **Reboot:** После `sudo reboot` сервер поднялся сам и сайт работает (проверка `restart: always`).

---

## Что мы изменили (Итоговое резюме):

* **Удален Systemd:** Docker Compose с флагом `restart: always` сделает ту же работу чище.
* **Удалено копирование SSL:** Теперь используем `readonly` проброс папки `/etc/letsencrypt` напрямую. Это гарантирует, что при обновлении ключей на сервере, Nginx внутри Docker увидит их мгновенно.
* **Исправлен SSL Renewal:** Добавлены хуки для управления контейнером Nginx.
* **Добавлен UFW:** Без открытия портов 80 и 443 в Ubuntu сайт бы не открылся.

**Готов начинать? Если хочешь, могу подсказать, как проверить статус А-записи прямо сейчас из консоли.**