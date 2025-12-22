# Testing & Scanning Guide

## Unit tests
```bash
pytest tests/unit/ -v --tb=short
# With coverage
pytest tests/unit/ --cov=src --cov-report=html --cov-fail-under=90
# Open report
open htmlcov/index.html  # or xdg-open on Linux
```

## Integration tests
Requires services (Postgres/Redis/RabbitMQ) running (e.g., via docker-compose.dev.yml).
```bash
pytest tests/integration/ -v --tb=short
pytest tests/integration/test_api.py::test_create_competitor -v
```

## E2E (Playwright)
```bash
cd frontend
npx playwright install chromium
npm run test:e2e          # headed
npm run test:e2e:ci       # headless
```

## Load testing (Locust)
```bash
locust -f tests/load/locustfile.py --host=https://api.example.com
# Browser UI at http://localhost:8089
# Headless example:
locust -f tests/load/locustfile.py --users=100 --spawn-rate=10 --run-time=10m --headless --csv=load_test_results
```

## Security scanning
```bash
# Bandit (Python vulns)
bandit -r src/ -f json -o bandit-report.json

# Safety (deps CVE)
safety scan --json --output safety-report.json

# Trivy (Docker images)
trivy image --severity HIGH,CRITICAL ci-backend:latest
```
