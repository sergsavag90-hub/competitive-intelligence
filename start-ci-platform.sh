#!/bin/bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_FILE="ci-platform-$(date +%Y%m%d-%H%M%S).log"
exec 3>&1 1>>"${LOG_FILE}" 2>&1

MODE=""
SKIP_MIGRATIONS=false
SKIP_TESTS=false

POSTGRES_PORT=5432
REDIS_PORT=6379
RABBITMQ_PORT=5672
BACKEND_PORT=8000
FRONTEND_PORT=3000
FLOWER_PORT=5555

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*" >&3; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $*" >&3; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&3; exit 1; }
info() { echo -e "${CYAN}[INFO]${NC} $*" >&3; }

check_port() {
    local port=$1
    local service=$2
    if lsof -i ":${port}" > /dev/null 2>&1; then
        error "Порт ${port} вже зайнято (${service})! Звільніть порт або змініть конфігурацію."
    fi
}

check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        error "Команда ${cmd} не знайдена! Встановіть її перед запуском."
    fi
}

check_requirements() {
    log "Перевірка системних вимог..."
    if [[ "$OSTYPE" != "linux-gnu"* && "$OSTYPE" != "darwin"* ]]; then
        error "Скрипт підтримує тільки Linux та macOS"
    fi
    check_command docker
    if ! docker info &> /dev/null; then
        error "Docker не запущено! Запустіть Docker daemon."
    fi
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        error "Docker Compose не встановлено!"
    fi
    check_command python3
    PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info >= (3, 11))')
    if [ "$PYTHON_VERSION" != "True" ]; then
        error "Потрібен Python 3.11+"
    fi
    check_command node
    check_command npm
    log "Всі вимоги задоволені! ✅"
}

setup_environment() {
    log "Налаштування середовища..."
    if [ ! -f .env ]; then
        info "Створення файлу .env..."
        ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        JWT_SECRET=$(openssl rand -base64 32)
        cat << EOF > .env
# === Database ===
DATABASE_URL=postgresql+asyncpg://ci_user:ci_password@localhost:5432/competitive_intelligence

# === Redis ===
REDIS_URL=redis://:ci_redis_pass@localhost:6379/0
REDIS_PASSWORD=ci_redis_pass

# === RabbitMQ ===
CELERY_BROKER_URL=amqp://ci_rabbit:ci_rabbit_pass@localhost:5672//
CELERY_RESULT_BACKEND=redis://:ci_redis_pass@localhost:6379/0

# === JWT ===
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === OpenTelemetry ===
OTEL_EXPORTER_JAEGER_AGENT_HOST=localhost
OTEL_SERVICE_NAME=competitive-intelligence

# === Encryption ===
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# === Environment ===
ENV=development
LOG_LEVEL=DEBUG

# === Database Pool ===
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50

# === Celery ===
CELERY_WORKERS=4
CELERY_CONCURRENCY=8

# === Ports ===
BACKEND_PORT=8000
FRONTEND_PORT=3000
FLOWER_PORT=5555
EOF
        log "Файл .env створено! ✅"
        warn "ЗБЕРЕЖІТЬ ЦІ ПАРОЛІ В БЕЗПЕЧНОМУ МІСЦІ!"
    else
        info ".env вже існує, пропускаю створення..."
    fi
    mkdir -p logs/{celery,backend,frontend}
}

start_docker_services() {
    log "Запуск Docker Compose сервісів..."
    check_port $POSTGRES_PORT "PostgreSQL"
    check_port $REDIS_PORT "Redis"
    check_port $RABBITMQ_PORT "RabbitMQ"
    if [ ! -f docker-compose.dev.yml ]; then
        info "Створення docker-compose.dev.yml..."
        cat << 'EOF' > docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    command: ["postgres", "-c", "max_connections=200", "-c", "shared_buffers=512MB"]
    environment:
      POSTGRES_DB: competitive_intelligence
      POSTGRES_USER: ci_user
      POSTGRES_PASSWORD: ci_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ci_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ci_redis_pass
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ci_rabbit
      RABBITMQ_DEFAULT_PASS: ci_rabbit_pass
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 30s
      retries: 3

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
EOF
    fi
    if [ ! -f init.sql ]; then
        echo "CREATE EXTENSION IF NOT EXISTS pgcrypto;" > init.sql
    fi
    $DOCKER_COMPOSE -f docker-compose.dev.yml up -d
    log "Очікування готовності сервісів..."
    sleep 10
    $DOCKER_COMPOSE -f docker-compose.dev.yml ps
}

run_migrations() {
    if [ "$SKIP_MIGRATIONS" = true ]; then
        info "Пропускаю міграції (--skip-migrations)"
        return
    fi
    log "Запуск Alembic міграцій..."
    source venv/bin/activate
    until python3 -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('postgresql://ci_user:ci_password@localhost:5432/competitive_intelligence'))" 2>/dev/null; do
        sleep 1
    done
    alembic upgrade head
    log "Міграції застосовано! ✅"
}

start_celery() {
    log "Запуск Celery Worker/Beat..."
    source venv/bin/activate
    nohup celery -A src.celery_app worker --loglevel=info --concurrency=8 --pool=threads -Q high-priority,low-priority \
        --logfile=logs/celery/worker.log --pidfile=logs/celery/worker.pid --detach
    nohup celery -A src.celery_app beat --loglevel=info --schedule=logs/celery/schedule.db \
        --logfile=logs/celery/beat.log --pidfile=logs/celery/beat.pid --detach
    sleep 5
    celery -A src.celery_app inspect active > /dev/null 2>&1 || warn "Celery inspect active failed"
}

start_backend() {
    log "Запуск FastAPI Backend..."
    source venv/bin/activate
    check_port $BACKEND_PORT "FastAPI Backend"
    nohup uvicorn backend.fastapi_app:app --host=0.0.0.0 --port=$BACKEND_PORT --workers=4 --log-level=info \
        --access-log --log-config=backend/logging.yml > logs/backend/backend.log 2>&1 &
    echo $! > logs/backend/backend.pid
    for i in {1..30}; do
        if curl -sf http://localhost:$BACKEND_PORT/health > /dev/null; then
            log "Backend запущено! ✅"
            return
        fi
        sleep 1
    done
    warn "Backend не відповідає, перевірте logs/backend/backend.log"
}

start_frontend() {
    log "Запуск React Frontend..."
    check_port $FRONTEND_PORT "React Frontend"
    pushd frontend >/dev/null
    nohup npm run preview -- --port=$FRONTEND_PORT --host=0.0.0.0 > ../logs/frontend/frontend.log 2>&1 &
    echo $! > ../logs/frontend/frontend.pid
    popd >/dev/null
    for i in {1..30}; do
        if curl -sf http://localhost:$FRONTEND_PORT > /dev/null; then
            log "Frontend запущено! ✅"
            return
        fi
        sleep 1
    done
    warn "Frontend не відповідає, перевірте logs/frontend/frontend.log"
}

show_status() {
    log "=== СТАТУС СЕРВІСІВ ==="
    echo ""
    info "Docker Containers:"
    $DOCKER_COMPOSE -f docker-compose.dev.yml ps 2>/dev/null || echo "Docker not running"
    echo ""
    info "Running Processes:"
    pgrep -f "celery.*worker" > /dev/null && echo "✅ Celery Worker: $(pgrep -f 'celery.*worker')" || echo "❌ Celery Worker: НЕ ЗАПУЩЕНО"
    pgrep -f "uvicorn.*fastapi_app" > /dev/null && echo "✅ FastAPI Backend: $(pgrep -f 'uvicorn.*fastapi_app')" || echo "❌ Backend: НЕ ЗАПУЩЕНО"
    pgrep -f "npm run preview" > /dev/null && echo "✅ Frontend: $(pgrep -f 'npm run preview')" || echo "❌ Frontend: НЕ ЗАПУЩЕНО"
    echo ""
    info "Health Checks:"
    curl -sf http://localhost:$BACKEND_PORT/health > /dev/null && echo "✅ Backend Health: OK" || echo "❌ Backend Health: FAILED"
    curl -sf http://localhost:$FRONTEND_PORT > /dev/null && echo "✅ Frontend: OK" || echo "❌ Frontend: FAILED"
}

stop_all() {
    log "Зупинка всіх сервісів..."
    $DOCKER_COMPOSE -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true
    for pidfile in logs/backend/backend.pid logs/celery/worker.pid logs/celery/beat.pid logs/frontend/frontend.pid; do
        if [ -f "$pidfile" ]; then
            kill $(cat "$pidfile") 2>/dev/null || true
            rm -f "$pidfile"
        fi
    done
    pkill -f "celery" 2>/dev/null || true
    log "Всі сервіси зупинено! ✅"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev) MODE="dev"; shift ;;
            --prod) MODE="prod"; shift ;;
            --local) MODE="local"; shift ;;
            --stop) MODE="stop"; shift ;;
            --status) MODE="status"; shift ;;
            --skip-migrations) SKIP_MIGRATIONS=true; shift ;;
            --skip-tests) SKIP_TESTS=true; shift ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "--dev | --prod | --local | --stop | --status | --skip-migrations | --skip-tests"
                exit 0
                ;;
            *) error "Невідомий параметр: $1. Використовуйте --help для допомоги." ;;
        esac
    done
}

main() {
    parse_args "$@"
    if [ -z "$MODE" ]; then
        MODE="dev"
        info "Режим не вказано, використовується --dev"
    fi
    case $MODE in
        dev)
            log "=== РОЗРОБНИЦЬКИЙ ЗАПУСК ==="
            check_requirements
            setup_environment
            start_docker_services
            run_migrations
            start_celery
            start_backend
            start_frontend
            show_status
            ;;
        prod)
            log "=== ПРОДАКШН ЗАПУСК (Docker Compose) ==="
            check_command docker
            check_command docker-compose
            if [ ! -f .env.production ]; then
                error "Файл .env.production не знайдено!"
            fi
            docker-compose -f docker-compose.yml up -d --build
            sleep 30
            show_status
            ;;
        local)
            log "=== ЛОКАЛЬНИЙ ЗАПУСК (БЕЗ Docker) ==="
            check_requirements
            setup_environment
            run_migrations
            start_celery
            start_backend
            start_frontend
            show_status
            ;;
        status)
            show_status
            ;;
        stop)
            stop_all
            ;;
        *)
            error "Невідомий режим: $MODE"
            ;;
    esac
}

trap stop_all INT
main "$@"
