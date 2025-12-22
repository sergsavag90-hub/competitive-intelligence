# Scanning API

- `POST /api/v1/scan/{competitor_id}` — trigger scan, returns `job_id`
- `GET /api/v1/scan/{job_id}/status` — check scan status
- `WS /ws/scan/{job_id}` — real-time updates
