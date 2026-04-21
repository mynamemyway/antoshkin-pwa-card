# План деплоя: Проект "Antoshkin PWA Card"

## 0. Конфигурация

**Сервер:** `ip`
**Пользователь:** `mynamemyway`
**Путь к проекту:** `/home/mynamemyway/projects/antoshkin-pwa-card`
**Домен:** `card.rassada1.ru` (требуется A-запись)

---

## Этап 1: Подготовка (Локально)

### 1.1. Конфиг окружения

Создать конфиг в `.env.production` файле. **Важно:** `DATABASE_URL` должен указывать на путь внутри контейнера.

```bash
# Database
DATABASE_URL=sqlite:///./data/loyalty.db

# SMS Service (SMS.ru)
SMS_API_KEY=""
SMS_TEST_MODE=false

# App Settings
DEBUG=True
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

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        proxy_pass http://app:8000/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

```

---

## Этап 3: Подготовка сервера

### 3.0. Подготовка директории проекта

* **Цель:** Перейти в директорию проектов на сервере
* **Команда:**
```bash
ssh mynamemyway@31.186.100.179
```

### 3.1. Инфраструктура и DNS

1. **DNS:** Убедись, что А-запись `card.rassada1.ru` → `31.186.100.179` активна (`ping card.rassada1.ru`).
2. **Firewall:** Открываем двери для веба.

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

3. **Перейти в директорию проектов:**

```bash
cd /home/mynamemyway/projects
```

---

## Этап 4: Магия SSL (Certbot)

**Критически важно:** Делаем это ДО запуска Docker, так как нам нужен свободный 80 порт.

### 4.1. **Установка:**
```bash
sudo apt update && sudo apt install certbot -y
```

### 4.2. **Получение:** - НЕ СДЕЛАНО (сделать после А-записи)
```bash
sudo certbot certonly --standalone \
  -d card.rassada1.ru \
  --email samokhvaloff.on@gmail.com \
  --agree-tos --non-interactive
```

*Теперь сертификаты лежат в `/etc/letsencrypt/live/`, и Docker увидит их через проброшенный volume.*

---

## Этап 5: Запуск и Автоматизация

### 5.1. Клонирование репозитория

* **Цель:** Получить код приложения на сервер и подготовить папки данных
* **Команда:**
```bash
cd /home/mynamemyway/projects
git clone https://github.com/mynamemyway/antoshkin-pwa-card.git
cd antoshkin-pwa-card
mkdir -p data logs backups
```

### 5.2. Копирование .env на сервер

**С локального Mac скопировать `.env.production` на сервер:**

```bash
scp .env.production mynamemyway@31.186.100.179:/home/mynamemyway/projects/antoshkin-pwa-card/.env
```

### 5.3. Старт приложения - СТОП - НЕ СДЕЛАНО (сделать после А-записи)

```bash
cd /home/mynamemyway/projects/antoshkin-pwa-card
docker-compose up -d --build
```

### 5.4. Авто-продление SSL (Бессмертный режим)

Настрой это одной командой:

```bash
sudo certbot renew --dry-run --pre-hook "docker-compose -f /home/mynamemyway/projects/antoshkin-pwa-card/docker-compose.yml stop nginx" --post-hook "docker-compose -f /home/mynamemyway/projects/antoshkin-pwa-card/docker-compose.yml start nginx"
```

---

## Этап 6: Тестирование и Обслуживание (Checklist)

### 6.1. Тестирование

1. [x] **HTTPS:** Замок в браузере горит зеленым.
2. [x] **Redirect:** При вводе `http://` перекидывает на `https://`.
3. [?] **PWA:** В меню Chrome (на Android) появился пункт "Установить приложение".
4. [x] **SMS:** Код пришел на телефон (не в логах, а в реальности).
5. [?] **Reboot:** После `sudo reboot` сервер поднялся сам и сайт работает (проверка `restart: always`).

### 6.2. Логирование

**Просмотр логов приложения:**

```bash
docker-compose logs -f app
```

**Просмотр логов nginx:**

```bash
docker-compose logs -f nginx
```

### 6.3. Резервное копирование БД

**Создать скрипт бэкапа:**

```bash
nano /home/mynamemyway/projects/antoshkin-pwa-card/backup-db.sh
```

**Содержимое:**

```bash
#!/bin/bash
PROJECT_DIR="/home/mynamemyway/projects/antoshkin-pwa-card"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp "$PROJECT_DIR/data/loyalty.db" "$BACKUP_DIR/loyalty_$DATE.db"
ls -t $BACKUP_DIR/*.db | tail -n +8 | xargs -r rm
```

**Сделать исполняемым:**

```bash
chmod +x /home/mynamemyway/projects/antoshkin-pwa-card/backup-db.sh
```

**Добавить в cron (ежедневно в 2:00):**

```bash
crontab -e
```

**Добавить строку:**

```cron
30 03 * * * /bin/bash /home/mynamemyway/projects/antoshkin-pwa-card/backup-db.sh >> /home/mynamemyway/projects/antoshkin-pwa-card/backups/backup.log 2>&1
```

---

## Что мы изменили (Итоговое резюме):

* **Порядок клонирования:** Сначала `git clone`, затем создание папки `data` внутри него, чтобы избежать конфликтов Git.
* **Удален Systemd:** Docker Compose с флагом `restart: always` сделает ту же работу чище.
* **Удалено копирование SSL:** Теперь используем `readonly` проброс папки `/etc/letsencrypt` напрямую.
* **Исправлен SSL Renewal:** Добавлены хуки для управления контейнером Nginx.
* **Добавлен UFW:** Без открытия портов 80 и 443 сайт бы не открылся.
* **Добавлены бэкапы:** Ежедневное резервное копирование БД с использованием абсолютных путей.

## Итоговый маршрут:
1. DNS/Ping — убеждаешься, что домен "видит" сервер.
2. UFW/Certbot — готовишь безопасность и SSL.
3. Git/SCP — заливаешь код и конфиг.
4. Docker Compose — запускаешь магию.
5. Cron — настраиваешь "бессмертие" и бэкапы.

# Обслуживание

### 1. Как проверить бэкап?

1. **Зайди в папку, куда сохраняются бэкапы** (допустим, это `~/backups`):
```bash
ls -lh ~/backups
```
*Ты должен увидеть файл с завтрашней датой и размером больше 0.*

---

### 2. Как обновить проект (например, добавить фавикон)

Cтандартный цикл обновления любого Docker-проекта после правок в коде или файлах.

1. **Перейди в папку проекта на сервере:**
```bash
cd ~/projects/antoshkin-pwa-card
```

2. **Затяни изменения из GitHub:**
```bash
git pull
```

3. **Пересобери и перезапусти контейнеры:**
```bash
docker-compose up -d --build
```

**Почему именно так?**

* `git pull` — обновляет файлы (включая твой новый фавикон).
* `--build` — заставляет Docker увидеть изменения в файлах и пересобрать образ `app`.
* `-d` — оставляет проект работать в фоне.

---

### Твой обновленный чек-лист обслуживания (Cheat Sheet):

| Задача | Команда |
| --- | --- |
| **Посмотреть логи** | `docker-compose logs -f app` |
| **Проверить статус** | `docker-compose ps` |
| **Обновить код** | `git pull && docker-compose up -d --build` |
| **Перезапустить всё** | `docker-compose restart` |
| **Удалить лишний мусор** | `docker system prune -f` |