# Competitive Intelligence Frontend

React 18 + Vite + TypeScript + MUI + Tailwind starter for the new dashboard.

## Scripts
- `npm run dev` – start dev server
- `npm run build` – production build
- `npm run preview` – preview build
- `npm run test` – jest
- `npm run lint` – eslint

## API Proxy
Dev server proxies `/api` and `/ws` to `http://localhost:8000` (FastAPI uvicorn).

## Docker
- Frontend: `frontend/Dockerfile` (multi-stage, nginx)
- Backend: `backend/Dockerfile` (uvicorn FastAPI)
- Compose: `docker-compose.frontend.yml` (ports: frontend 4173→80, api 8000)

## Structure
- `src/api` – axios client (JWT cookie refresh)
- `src/hooks` – data/websocket hooks
- `src/components` – UI building blocks (AG Grid table, scan progress)
- `src/pages/App.tsx` – demo dashboard
- `src/types` – API types

## WS Status
`useScanStatus(jobId)` connects to `/ws/scan/{jobId}` for real-time updates.
