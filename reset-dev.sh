#!/bin/bash
# Quick cleanup for dev stack: stop containers on db/redis/rabbit ports and kill stray dev servers.
set -euo pipefail

echo "[reset-dev] Stopping dev compose stacks (if any)..."
docker compose -f docker-compose.dev.yml down --remove-orphans >/dev/null 2>&1 || true

echo "[reset-dev] Removing lingering dev containers..."
docker rm -f ci-postgres-dev ci-redis-dev ci-rabbit-dev >/dev/null 2>&1 || true

echo "[reset-dev] Freeing ports 5432/6379/5672 (DB/Redis/Rabbit)..."
for port in 5432 6379 5672; do
  if lsof -i ":$port" -t >/dev/null 2>&1; then
    pids=$(lsof -i ":$port" -t | sort -u)
    echo "  killing PIDs on $port: $pids"
    kill -9 $pids >/dev/null 2>&1 || true
  fi
done

echo "[reset-dev] Killing stray backend/frontend dev servers..."
# Backend (uvicorn) common ports
for port in 8000 8100; do
  if lsof -i ":$port" -t >/dev/null 2>&1; then
    pids=$(lsof -i ":$port" -t | sort -u)
    echo "  killing PIDs on $port: $pids"
    kill -9 $pids >/dev/null 2>&1 || true
  fi
done

# Frontend dev ports
for port in 3000 3100 3200 3300 3400 3500 3600; do
  if lsof -i ":$port" -t >/dev/null 2>&1; then
    pids=$(lsof -i ":$port" -t | sort -u)
    echo "  killing PIDs on $port: $pids"
    kill -9 $pids >/dev/null 2>&1 || true
  fi
done

echo "[reset-dev] Cleanup complete. Re-run ./start-ci-platform.sh --dev --skip-migrations"
