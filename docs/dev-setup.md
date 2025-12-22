# Local Development Setup

## Prerequisites
- CPU: 4 cores (8+ for production), RAM: 8GB (16GB prod), Disk: 50GB SSD (200GB prod)
- OS: Ubuntu 22.04+ or macOS 13+
- Tools: git, curl, docker, docker-compose, Python 3.11, Node.js 20+

Install basics (Ubuntu):
```bash
sudo apt update && sudo apt install -y git curl wget build-essential python3.11 python3.11-venv docker.io docker-compose
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## Clone
```bash
git clone https://github.com/sergsavag90-hub/competitive-intelligence.git
cd competitive-intelligence
```

## Environment
Create `.env` in repo root:
```bash
cat << 'EOF' > .env
DATABASE_URL=postgresql+asyncpg://ci_user:ci_password@localhost:5432/competitive_intelligence
REDIS_URL=redis://:ci_redis_pass@localhost:6379/0
CELERY_BROKER_URL=amqp://ci_rabbit:ci_rabbit_pass@localhost:5672//
CELERY_RESULT_BACKEND=redis://:ci_redis_pass@localhost:6379/0
JWT_SECRET=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OTEL_SERVICE_NAME=competitive-intelligence
ENV=development
EOF
```

## Start infra (Postgres, Redis, RabbitMQ)
```bash
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml ps
```

## Python env
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Database migrations
```bash
alembic current
alembic upgrade head
```

## Run services
- Celery worker: `celery -A src.celery_app worker -l info --concurrency=4 -Q high-priority,low-priority`
- Celery beat: `celery -A src.celery_app beat -l info --schedule=/tmp/celerybeat-schedule`
- FastAPI: `uvicorn backend.fastapi_app:app --host 0.0.0.0 --port 8000 --reload`
- Frontend:
  ```bash
  cd frontend
  npm install
  npm run dev -- --port=3000 --host=0.0.0.0
  ```

## Notes
- Flower (monitor Celery): `celery -A src.celery_app flower --port=5555`
- Health: `curl http://localhost:8000/health`
- Web UI: http://localhost:3000
