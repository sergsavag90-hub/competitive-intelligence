# Monitoring & Logs

## Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Filtered
docker-compose logs -f backend | grep "ERROR"
```

## Prometheus
- UI: http://localhost:9090
- Useful queries:
  - `rate(ci_scans_total[5m])`
  - `histogram_quantile(0.95, ci_scan_duration_seconds)`
  - `ci_active_scans`
  - `redis_connected_clients`

## Grafana
- UI: http://localhost:3001 (default `admin/admin123` unless overridden)
- Datasource: Prometheus `http://prometheus:9090`
- Import dashboards (examples):
  - 1860 (Redis)
  - 3662 (Docker)
  - 6417 (Node Exporter host metrics)
  - 12559 (Postgres)

## Tips
- For JSON/structured logs, prefer piping to `jq`:
  ```bash
  docker-compose logs backend | jq -r 'select(.level=="error")'
  ```
- Expose `/metrics` from FastAPI/backend to Prometheus; Jaeger UI at `http://localhost:16686`.
