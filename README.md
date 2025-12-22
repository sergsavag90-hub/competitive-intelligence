# 📊 Competitive Intelligence Platform

**Enterprise-Ready System for Automated Competitor Analysis & Market Intelligence**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Зміст

1. [Опис проекту](#-опис-проекту)
2. [Архітектура](#-архітектура)
3. [Ключові можливості](#-ключові-можливості)
4. [Швидкий старт](#-швидкий-старт)
5. [Детальна установка](#-детальна-установка)
6. [Конфігурація](#-конфігурація)
7. [Використання](#-використання)
8. [Модулі скрапінгу](#-модулі-скрапінгу)
9. [Система задач](#-система-задач-celery)
10. [Аутентифікація](#-аутентифікація-та-авторизація)
11. [Моніторинг](#-моніторинг-та-спостереження)
12. [Тестування](#-тестування)
13. [Продакшн деплоймент](#-продакшн-депоймент-proxmox)
14. [Типові проблеми](#-типові-проблеми-та-вирішення)
15. [Розробка](#-розробка-та-внесок)
16. [Ліцензія](#-ліцензія)

---

## 🎯 Опис проекту

**Competitive Intelligence Platform** — це повноцінна enterprise-система автоматизованого моніторингу конкурентів у мережі. Система дозволяє відстежувати ціни, промо-акції, SEO-стратегії, контактну інформацію та асортимент товарів конкурентів у реальному часі.

**Застосування:**
- E-commerce моніторинг цін
- B2B аналіз послуг конкурентів
- SEO конкурентна розвідка
- Маркетинговий аналіз промо-акцій
- Прогнозування цін (ML)

---

## 🏗️ Архітектура

```mermaid
graph TB
    subgraph Frontend
        React[React 18 + TypeScript]
        MUI[Material-UI]
        Recharts[Recharts.js]
        WSS[WebSocket Client]
    end

    subgraph API Gateway
        FastAPI[FastAPI + Uvicorn]
        JWT[JWT Auth]
        RBAC[RBAC Middleware]
        GraphQL[GraphQL Endpoint]
        WSServer[WebSocket Server]
    end

    subgraph Background Workers
        Celery[Celery Workers]
        Beat[Celery Beat Scheduler]
        Scrapers[Selenium Grid Scrapers]
        Ollama[Local LLM (Ollama)]
    end

    subgraph Database Layer
        PostgreSQL[(PostgreSQL 15)]
        Redis[(Redis Cache)]
        Timescale[TimescaleDB (Price History)]
    end

    subgraph Observability
        Jaeger[Jaeger Tracing]
        Prometheus[Prometheus Metrics]
        Grafana[Grafana Dashboards]
        Loki[Loki Logs]
    end

    React --> FastAPI
    React --> WSServer
    FastAPI --> JWT
    FastAPI --> PostgreSQL
    FastAPI --> Redis
    FastAPI --> Jaeger
    FastAPI --> Prometheus
    Celery --> Scrapers
    Celery --> Ollama
    Celery --> PostgreSQL
    Celery --> Redis
    Scrapers --> SeleniumHub[Selenium Grid Hub]
    SeleniumHub --> ChromeNodes[Chrome Nodes]
    SeleniumHub --> FirefoxNodes[Firefox Nodes]
    PostgreSQL --> Timescale
    Redis --> Prometheus
    Jaeger --> Grafana
    Prometheus --> Grafana
    Loki --> Grafana
```

---

## ✨ Ключові можливості

| Категорія | Опис |
|-----------|------|
| **Скрапінг** | Selenium Grid 4 для обходу JS-рендерінгу, CAPTCHA bypass, proxy rotation |
| **База даних** | PostgreSQL 15 + TimescaleDB для часових рядів, Redis для кешу |
| **Аналітика** | Prophet для прогнозування цін, Isolation Forest для аномалій, Ollama для інсайтів |
| **API** | FastAPI + GraphQL, WebSocket для real-time updates, JWT auth |
| **UI** | React 18 + TypeScript, Material-UI, real-time dashboards |
| **Фонові задачі** | Celery + RabbitMQ, priority queues, retry logic, DLQ |
| **Моніторинг** | OpenTelemetry, Jaeger, Prometheus, Grafana, Loki |
| **Безпека** | Field-level encryption, RBAC, audit logs, rate limiting |
| **Тестування** | Unit, integration, E2E (Playwright), load tests (Locust) |
| **Деплоймент** | Docker Compose, Proxmox VE, GitOps (ArgoCD) |

---

## 🚀 Швидкий старт

**Найпростіший спосіб запустити всю платформу:**

```bash
# 1. Клонуйте репозиторій
git clone https://github.com/sergsavag90-hub/competitive-intelligence.git
cd competitive-intelligence

# 2. Зробіть скрипт виконуваним
chmod +x start-ci-platform.sh

# 3. Запустіть у розробницькому режимі
./start-ci-platform.sh --dev

# 4. Перегляньте статус
./start-ci-platform.sh --status

# 5. Доступ до сервісів:
#    Frontend: http://localhost:3000
#    API Docs: http://localhost:8000/docs
#    RabbitMQ: http://localhost:15672 (ci_rabbit/ci_rabbit_pass)
```

**Примітки:**
- Скрипт автоматично створить `.env` файл з генерацією секретних ключів
- Для продакшн режиму створіть `.env.production` файл
- Всі логи зберігаються в `./logs/`

---

## 🔧 Детальна установка

### **Системні вимоги**

```bash
# Мінімальні вимоги для development:
# - CPU: 4 cores, RAM: 8GB, Disk: 50GB SSD
# - OS: Ubuntu 22.04+ або macOS 13+
# - Docker + Docker Compose
# - Python 3.11+, Node.js 18+

# Встановлення на Ubuntu:
sudo apt update
sudo apt install -y python3.11 python3.11-venv nodejs npm docker.io docker-compose

# Встановлення на macOS:
brew install python@3.11 node docker
```

### **Ручна установка (без скрипта)**

```bash
# 1. Клонування
git clone https://github.com/sergsavag90-hub/competitive-intelligence.git
cd competitive-intelligence

# 2. Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Node.js dependencies
cd frontend && npm install && cd ..

# 4. Змінні оточення
cp .env.example .env
# Редагувати .env з вашими значеннями

# 5. Запуск базових сервісів (Docker)
docker-compose -f docker-compose.dev.yml up -d

# 6. Alembic міграції
alembic upgrade head

# 7. Запуск Celery
celery -A src.celery_app worker --loglevel=info --concurrency=8 &
celery -A src.celery_app beat --loglevel=info &

# 8. Запуск FastAPI
uvicorn backend.fastapi_app:app --host=0.0.0.0 --port=8000 --reload &

# 9. Запуск React
cd frontend && npm run dev -- --port=3000 &
```

---

## ⚙️ Конфігурація

### **Файл `.env`**

```bash
# === Core ===
ENV=development|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# === Database ===
DATABASE_URL=postgresql+asyncpg://user:pass@pgbouncer:6432/ci
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50

# === Redis ===
REDIS_URL=redis://:password@redis:6379/0
REDIS_PASSWORD=strong_redis_pass

# === RabbitMQ (Celery) ===
CELERY_BROKER_URL=amqp://user:pass@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://:password@redis:6379/0
CELERY_WORKERS=4
CELERY_CONCURRENCY=8

# === JWT Auth ===
JWT_SECRET=your_jwt_secret_key_32+chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === OpenTelemetry ===
OTEL_EXPORTER_JAEGER_AGENT_HOST=jaeger
OTEL_SERVICE_NAME=ci-platform
OTEL_LOG_LEVEL=info

# === Encryption ===
ENCRYPTION_KEY=fernet_key_here  # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# === Selenium Grid ===
SELENIUM_GRID_URL=http://selenium-hub:4444/wd/hub
SELENIUM_BROWSER=chrome
SELENIUM_TIMEOUT=30

# === Ports ===
BACKEND_PORT=8000
FRONTEND_PORT=3000
FLOWER_PORT=5555
```

### **Файл `config.yaml`**

```yaml
# Налаштування скрапінгу
scraping:
  default_delay: 2  # секунди між запитами
  max_depth: 3  # глибина сканування
  user_agent: "Mozilla/5.0 (CI-Bot/1.0)"
  stealth_mode: true
  proxy_rotation: true
  proxy_provider: "brightdata"  # або "oxylabs"

# Target competitors
targets:
  - name: "Amazon"
    url: "https://amazon.com"
    scan_interval: "daily"
    priority: "high"
    modules: ["products", "prices", "promotions"]
    
  - name: "Ebay"
    url: "https://ebay.com"
    scan_interval: "weekly"
    priority: "medium"
    modules: ["products", "seo"]

# ML Analytics
analytics:
  forecasting:
    enabled: true
    model: "prophet"
    retrain_interval: "7d"
    
  anomaly_detection:
    enabled: true
    contamination: 0.05
    alert_threshold: 0.8
    
  clustering:
    enabled: true
    n_clusters: 3
    run_schedule: "0 2 * * 0"

# Notifications
notifications:
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#alerts"
    
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"
    
  email:
    enabled: true
    smtp_host: "smtp.sendgrid.net"
    smtp_user: "${SMTP_USER}"
    smtp_pass: "${SMTP_PASS}"

# Rate limiting
rate_limit:
  default: "100/minute"
  authenticated: "1000/minute"
  admin: "10000/minute"
```

---

## 🎮 Використання

### **CLI (Командний рядок)**

```bash
# Запуск повного сканування
python run_intelligence.py --full

# Сканування конкретного конкурента
python run_intelligence.py --target "Amazon" --modules products,prices

# Сканування з пріоритетом
python run_intelligence.py --target "Amazon" --priority high --queue high-priority

# Перегляд статусу задач
celery -A src.celery_app inspect active

# Виклик API endpoint
curl -X POST "http://localhost:8000/api/v1/scans" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"competitor_id": "uuid-here", "modules": ["products", "seo"]}'
```

### **API Endpoints (FastAPI)**

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/v1/auth/token` | Login (JWT) | Public |
| `POST` | `/api/v1/auth/refresh` | Refresh token | Public |
| `GET` | `/api/v1/me` | Current user | JWT |
| `GET` | `/api/v1/competitors` | List competitors | JWT |
| `POST` | `/api/v1/competitors` | Create competitor | JWT (admin) |
| `GET` | `/api/v1/competitors/{id}` | Get competitor details | JWT |
| `POST` | `/api/v1/competitors/{id}/scan` | Trigger scan | JWT (analyst+) |
| `GET` | `/api/v1/competitors/{id}/products` | Get products (paginated) | JWT |
| `GET` | `/api/v1/competitors/{id}/prices/history` | Price history | JWT |
| `GET` | `/api/v1/competitors/{id}/seo` | SEO data | JWT |
| `GET` | `/api/v1/analytics/forecast/{product_id}` | Price forecast | JWT |
| `GET` | `/api/v1/analytics/anomalies` | Anomaly detection | JWT |
| `GET` | `/api/v1/alerts` | User alerts | JWT |
| `WS` | `/ws/scan/{job_id}` | Real-time scan status | JWT |
| `GET` | `/health` | Health check | Public |
| `GET` | `/metrics` | Prometheus metrics | Public |

**Приклади API calls:**

```bash
# 1. Login
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=Admin123!" | jq -r .access_token)

# 2. Get competitors
curl -X GET "http://localhost:8000/api/v1/competitors" \
  -H "Authorization: Bearer $TOKEN"

# 3. Trigger scan
curl -X POST "http://localhost:8000/api/v1/competitors/123/scan" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"modules": ["products", "prices"], "priority": "high"}'

# 4. WebSocket connection (requires wscat)
wscat -c "ws://localhost:8000/ws/scan/job-123?token=$TOKEN"
```

### **Web UI (React)**

**Головні сторінки:**
- **Dashboard** (`/`) — Огляд всіх конкурентів, графіки змін цін
- **Competitor Detail** (`/competitors/:id`) — Детальна інформація, таблиці товарів
- **Analytics** (`/analytics`) — Прогнози, аномалії, кластеризація
- **Alerts** (`/alerts`) — Сповіщення та налаштування
- **Admin Panel** (`/admin`) — Керування користувачами, аудит логи

**Функціонал UI:**
- Real-time WebSocket updates при скануванні
- Infinite scroll таблиці з 10k+ товарів
- Інтерактивні графіки цін (Recharts)
- Експорт до Excel/CSV
- Dark mode toggle

---

## 🔍 Модулі скрапінгу

### **1. SEO Intelligence (`seo_scraper.py`)**
```python
# Збирає:
- Title, meta keywords, description
- H1-H6 структура
- robots.txt, sitemap.xml
- JSON-LD schema.org
- Open Graph теги
- Internal linking structure
- Mobile responsiveness check
```

### **2. Company Data (`company_scraper.py`)**
```python
# Збирає:
- Email (захищений regex)
- Телефони (мультиформат)
- Адреси (NLP parsing)
- Соціальні мережі (Facebook, Instagram, LinkedIn)
- Контактні форми
- Час роботи
- Логотипи
```

### **3. Products (`product_scraper.py`)**
```python
# Збирає:
- Назва, SKU, категорії
- Ціна (вкл. валюту)
- Опис, специфікації
- Зображення (завантаження в S3/MinIO)
- Наявність (in stock)
- Варіації (розміри, кольори)
- Правила ML для виявлення product cards
```

### **4. Promotions (`promotion_scraper.py`)**
```python
# Збирає:
- Акції (відсотки, суми)
- Промо-коди
- Flash sales
- Сезонні пропозиції
- Умови участі
- Дати початку/завершення
- Аналіз змін vs попередніх сканувань
```

### **5. Protection Bypass**
```python
# Обхід захистів:
- 2Captcha/Anti-Captcha integration
- Proxy rotation (BrightData/Oxylabs)
- Selenium Stealth
- User-Agent rotation
- Cloudflare bypass headers
- Rate limiting adaptive
```

---

## ⚙️ Система задач Celery

### **Структура queues**
```python
# High Priority Queue
@celery_app.task(queue='high-priority', max_retries=3)
def scrape_priority_competitor(competitor_id: UUID):
    # Запускається негайно
    pass

# Low Priority Queue
@celery_app.task(queue='low-priority', rate_limit='10/m')
def scrape_regular_competitor(competitor_id: UUID):
    # Запускається в background
    pass

# Background Queue
@celery_app.task(queue='background')
def cleanup_old_snapshots(days: int = 30):
    # Щоденне очищення
    pass
```

### **Celery Beat Schedule**
```python
# Щоденно о 3:00
'daily-scan': {
    'task': 'src.tasks.scraping_tasks.scrape_all_competitors',
    'schedule': crontab(hour=3, minute=0),
    'args': (['products', 'prices'],),
    'options': {'queue': 'low-priority'}
}

# Щотижня в неділю о 6:00
'weekly-report': {
    'task': 'src.tasks.analytics_tasks.generate_weekly_report',
    'schedule': crontab(day_of_week=0, hour=6, minute=0),
}

# Кожні 15 хвилин (health check)
'health-check': {
    'task': 'src.tasks.monitoring_tasks.check_system_health',
    'schedule': 900.0,
}
```

### **Моніторинг Celery (Flower)**
```bash
# Запуск Flower UI
celery -A src.celery_app flower --port=5555

# Доступ: http://localhost:5555
# Можливості:
# - Перегляд active tasks
# - Restart failed tasks
# - Rate limiting graphs
# - Worker status
```

---

## 🔐 Аутентифікація та авторизація

### **JWT Tokens**
```python
# Структура токена:
{
  "sub": "user-uuid",
  "type": "access|refresh",
  "role": "admin|analyst|viewer",
  "version": 1,  # Для відкликання
  "exp": 1234567890
}
```

### **Ролі та права доступу**

| Роль | API Access | Scan Trigger | View Data | Admin Panel |
|------|------------|--------------|-----------|-------------|
| **admin** | Full | ✅ | ✅ | ✅ |
| **analyst** | Most endpoints | ✅ | ✅ | ❌ |
| **viewer** | Read-only | ❌ | ✅ | ❌ |

### **Відкликання токенів**
```python
# Якщо пароль змінено:
user.token_version += 1
db.save(user)

# Всі існуючі токени стають недійсними
```

---

## 📊 Моніторинг та спостереження

### **OpenTelemetry Tracing**

```python
# В кожному запиті додається trace_id
# Заголовок: X-Trace-ID: 4bf92f3577b34da5

# Перегляд трейсів у Jaeger:
# http://localhost:16686
# Search by: service.name="competitive-intelligence"
#           operation.name="scrape_competitor"
```

### **Prometheus Metrics**

| Метрика | Тип | Опис |
|---------|-----|------|
| `ci_scans_total` | Counter | Кількість сканувань за статусом |
| `ci_scan_duration_seconds` | Histogram | Час сканування (p50, p95, p99) |
| `ci_active_scans` | Gauge | Активні сканування зараз |
| `ci_queue_depth` | Gauge | Кількість задач у черзі |
| `ci_api_requests_total` | Counter | HTTP запити за статусом |
| `ci_database_query_duration_seconds` | Histogram | Час SQL запитів |

### **Grafana Dashboards**

**Імпорт дашбордів:**
```bash
# Grafana → Dashboards → Import
# Dashboard ID: 1860 (Redis)
# Dashboard ID: 13981 (PostgreSQL)
# Dashboard ID: 8673 (FastAPI)
```

**Кастомний dashboard:**
```json
{
  "panels": [
    {
      "title": "Scan Success Rate",
      "targets": [{"expr": "rate(ci_scans_total{status='success'}[5m])"}]
    },
    {
      "title": "Price Anomalies",
      "targets": [{"expr": "ci_anomalies_detected_total"}]
    }
  ]
}
```

---

## 🧪 Тестування

### **Unit Tests**
```bash
# Запуск всіх unit tests
pytest tests/unit/ -v --tb=short

# З покриттям
pytest tests/unit/ --cov=src --cov-report=html --cov-fail-under=90

# Перегляд звіту
open htmlcov/index.html
```

### **Integration Tests**
```bash
# Потрібні запущені сервіси
pytest tests/integration/ -v --tb=short

# Тестування API
pytest tests/integration/test_api.py::test_create_competitor -v
```

### **E2E Tests (Playwright)**
```bash
cd frontend

# Встановити browsers
npx playwright install chromium

# Запуск
npm run test:e2e

# CI mode
npm run test:e2e:ci
```

### **Load Tests (Locust)**
```bash
# Запуск
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Автоматизований
locust -f tests/load/locustfile.py --users=100 --spawn-rate=10 --run-time=10m --headless --csv=results
```

---

## 🏭 Продакшн деплоймент (Proxmox)

### **Автоматичний деплой через скрипт**

```bash
# На Proxmox хості
cd /tmp
git clone https://github.com/sergsavag90-hub/competitive-intelligence.git
cd competitive-intelligence/proxmox

# Створити LXC контейнер
./create-lxc.sh 100 ci-production dhcp

# Увійти в контейнер
pct enter 100

# В контейнері
cd /opt/competitive-intelligence
./deploy.sh
```

### **Ручний деплой (для розуміння)**

```bash
# 1. Підготовка LXC контейнера
pct create 100 /var/lib/vz/template/cache/debian-12-standard_12.2-1_amd64.tar.gz \
  --hostname ci-production \
  --cores 4 \
  --memory 8192 \
  --swap 1024 \
  --rootfs 50 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --onboot 1

pct start 100
pct enter 100

# 2. Встановлення ПЗ
apt update && apt install -y docker.io docker-compose git python3.11 python3.11-venv

# 3. Clone repo
cd /opt && git clone <repo-url> competitive-intelligence
cd competitive-intelligence

# 4. Налаштування
cp .env.example .env.production
# Редагувати .env.production

# 5. Docker Compose
docker-compose -f docker-compose.yml up -d

# 6. Міграції
docker-compose exec backend alembic upgrade head

# 7. Створення суперпользователя
docker-compose exec backend python scripts/init_superuser.py
```

### **Налаштування Reverse Proxy (Traefik)**

```yaml
# docker-compose.yml (частина)
traefik:
  command:
    - "--api.dashboard=true"
    - "--providers.docker=true"
    - "--entrypoints.websecure.address=:443"
    - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
    - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
  ports:
    - "80:80"
    - "443:443"
```

---

## 🛠️ Типові проблеми та вирішення

### **1. Порт вже зайнято**
```bash
# Знайти процес
sudo lsof -i :5432

# Вбити процес
kill -9 $(lsof -ti:5432)

# Або змінити порт у .env
DB_PORT=5433
```

### **2. Alembic міграції "зависають"**

```bash
# Перевірити active locks
SELECT * FROM pg_locks WHERE NOT granted;

# Очистити alembic_version
docker-compose exec postgres psql -U ci_user -d ci -c "DROP TABLE alembic_version;"

# Перезапустити
alembic stamp head
alembic upgrade head
```

### **3. Celery worker не бачить задачі**
```bash
# Перевірити підключення до RabbitMQ
docker-compose exec rabbitmq rabbitmqctl list_queues

# Перевірити Celery config
celery -A src.celery_app inspect ping

# Перевірити logs
tail -f logs/celery/worker.log
```

### **4. Postgres connection pool exhausted**
```bash
# Збільшити pool size у .env
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100

# Додати pgbouncer
docker-compose up -d pgbouncer
# Змінити DATABASE_URL на pgbouncer:6432
```

### **5. Redis OOM**
```bash
# Перевірити використання пам'яті
docker-compose exec redis redis-cli info memory

# Додати maxmemory policy до redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### **6. Selenium Grid node не запускається**
```bash
# Перевірити логи
docker-compose logs selenium-node-chrome

# Перевірити ресурси
docker stats

# Очистити образи
docker system prune -a
```

---

## 🤝 Розробка та внесок

### **Git Workflow**
```bash
# 1. Створити feature branch
git checkout -b feature/new-scraper-module

# 2. Code style (Black + isort)
black src/ tests/
isort src/ tests/

# 3. Type checks (mypy)
mypy src/

# 4. Lint (ruff)
ruff check src/ tests/

# 5. Tests
pytest tests/unit/ --cov=src --cov-fail-under=90

# 6. Commit (conventional commits)
git commit -m "feat: add new promo scraper module"

# 7. Push та PR
git push origin feature/new-scraper-module
```

### **Pre-commit hooks**
```bash
# Встановити pre-commit
pip install pre-commit
pre-commit install

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
```

---

## 📜 Ліцензія

**MIT License**

Copyright (c) 2024 SergSavag90

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions...

---

## 📞 Підтримка

- **GitHub Issues**: [Report Bug/Feature](https://github.com/sergsavag90-hub/competitive-intelligence/issues)
- **Email**: support@competitive-intelligence.com
- **Discord**: [Join Community](https://discord.gg/competitive-intelligence)

---

## 🙏 Подяки

- [FastAPI](https://fastapi.tiangolo.com/) - за неймовірний фреймворк
- [Selenium](https://www.selenium.dev/) - за веб-автоматизацію
- [Celery](https://docs.celeryq.dev/) - за distributed tasks
- [Ollama](https://ollama.ai/) - за локальний LLM
- [TimescaleDB](https://www.timescale.com/) - за часові ряди
- [Jaeger](https://www.jaegertracing.io/) - за tracing
- [Grafana](https://grafana.com/) - за візуалізацію

---

**⭐ Якщо вам сподобався проект, будь ласка, поставте зірку на GitHub! ⭐**
