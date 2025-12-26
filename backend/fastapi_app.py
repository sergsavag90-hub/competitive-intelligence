import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import uuid

from src.database.db_manager import DatabaseManager
from backend.websockets.scan_status import ScanStatusManager
from backend.auth import ACCESS_COOKIE, router as auth_router, init_jwt, decode_token
from backend.dependencies import require_role
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


db = DatabaseManager()
scan_manager = ScanStatusManager()
executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(
    title="Competitive Intelligence API",
    description="Enterprise-grade API for competitor monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
frontend_origins = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:4173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIdMiddleware)
init_jwt(app)
app.include_router(auth_router)
FastAPIInstrumentor.instrument_app(app)


@app.on_event("startup")
async def startup_event():
    await db.backend.init()


class CompetitorOut(BaseModel):
    id: int
    name: str
    url: str
    priority: int
    enabled: bool
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class SEOResponse(BaseModel):
    title: Optional[str]
    meta_description: Optional[str]
    meta_keywords: Optional[str]
    h1_tags: Optional[List[str]]
    h2_tags: Optional[List[str]]
    robots_txt: Optional[str]
    sitemap_url: Optional[str]
    structured_data: Optional[Dict]
    internal_links_count: Optional[int]
    external_links_count: Optional[int]
    page_load_time: Optional[float]
    collected_at: Optional[datetime]


class ScanTriggerResponse(BaseModel):
    job_id: str
    status: str = "queued"


class ScanStatus(BaseModel):
    status: str
    progress: int = 0
    result: Optional[Dict] = None
    error: Optional[str] = None


class PagedCompetitors(BaseModel):
    items: List[CompetitorOut]
    total: int


class ProductOut(BaseModel):
    id: int
    name: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    url: Optional[str]
    category: Optional[str]
    in_stock: Optional[bool]
    main_image: Optional[str]
    last_seen: Optional[datetime] = None

    class Config:
        orm_mode = True


class ProductsPage(BaseModel):
    items: List[ProductOut]
    page: int
    size: int
    total: int


scan_jobs: Dict[str, ScanStatus] = {}


async def run_scan_job(job_id: str, competitor_id: int) -> None:
    scan_jobs[job_id] = ScanStatus(status="running", progress=5)
    await scan_manager.broadcast(job_id, {"status": "running", "progress": 5})
    # Minimal placeholder: simulate progress; integrate real scan runner later
    for step in (25, 50, 75, 100):
        await asyncio.sleep(1)
        scan_jobs[job_id].progress = step
        await scan_manager.broadcast(job_id, {"status": "running", "progress": step})
    scan_jobs[job_id].status = "completed"
    await scan_manager.broadcast(job_id, {"status": "completed", "progress": 100})


def run_in_thread(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return asyncio.create_task(coro)
    return loop.run_until_complete(coro)


def _stream_products_csv(items: List[ProductOut]):
    header = "id,name,price,currency,url,category,in_stock,main_image,last_seen\n"

    async def generator():
        yield header
        for p in items:
            row = [
                str(p.id),
                (p.name or "").replace(",", " "),
                str(p.price or ""),
                p.currency or "",
                p.url or "",
                p.category or "",
                "1" if p.in_stock else "0",
                p.main_image or "",
                p.last_seen.isoformat() if p.last_seen else "",
            ]
            yield ",".join(row) + "\n"

    return generator()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    # Could extend with DB/Redis pings; keep lightweight for probes
    return {"status": "ready"}


@app.get("/api/v1/competitors", response_model=List[CompetitorOut])
async def list_competitors(user=Depends(require_role("viewer"))) -> List[CompetitorOut]:  # noqa: B008
    competitors = await db.backend.get_all_competitors(enabled_only=False)
    return [CompetitorOut.from_orm(c) for c in competitors]


@app.get("/api/v1/competitors/paged", response_model=PagedCompetitors)
async def list_competitors_paged(
    offset: int = 0,
    limit: int = 100,
    user=Depends(require_role("viewer")),  # noqa: B008
):
    competitors = await db.backend.get_all_competitors(enabled_only=False)
    total = len(competitors)
    sliced = competitors[offset : offset + limit]
    return PagedCompetitors(items=[CompetitorOut.from_orm(c) for c in sliced], total=total)


@app.get("/api/v1/products", response_model=ProductsPage)
async def get_products(
    competitor_id: int = Query(..., ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    stream: bool = Query(False),
    user=Depends(require_role("viewer")),  # noqa: B008
):
    """
    Paginated products endpoint with optional CSV streaming. Caching happens inside db.get_products_paginated (Redis).
    """
    payload = await db.backend.get_products_paginated(competitor_id, page=page, size=size)
    items = [ProductOut(**item) for item in payload.get("items", [])]

    if stream:
        return StreamingResponse(_stream_products_csv(items), media_type="text/csv")

    return ProductsPage(
        items=items,
        page=payload.get("page", page),
        size=payload.get("size", size),
        total=payload.get("total", 0),
    )


@app.get("/api/v1/competitors/{competitor_id}/seo", response_model=SEOResponse)
async def get_competitor_seo(competitor_id: int, user=Depends(require_role("viewer"))):  # noqa: B008
    seo = await db.backend.get_latest_seo_data(competitor_id)
    if not seo:
        raise HTTPException(status_code=404, detail="SEO data not found")
    return SEOResponse(
        title=seo.title,
        meta_description=seo.meta_description,
        meta_keywords=seo.meta_keywords,
        h1_tags=seo.h1_tags,
        h2_tags=seo.h2_tags,
        robots_txt=seo.robots_txt,
        sitemap_url=seo.sitemap_url,
        structured_data=seo.structured_data,
        internal_links_count=seo.internal_links_count,
        external_links_count=seo.external_links_count,
        page_load_time=seo.page_load_time,
        collected_at=seo.collected_at,
    )


@app.post("/api/v1/scan/{competitor_id}", response_model=ScanTriggerResponse)
async def trigger_scan(competitor_id: int, background_tasks: BackgroundTasks, user=Depends(require_role("analyst"))):  # noqa: B008
    job_id = str(uuid4())
    scan_jobs[job_id] = ScanStatus(status="queued", progress=0)
    background_tasks.add_task(run_scan_job, job_id, competitor_id)
    return ScanTriggerResponse(job_id=job_id, status="queued")


@app.get("/api/v1/scan/{job_id}/status", response_model=ScanStatus)
async def scan_status(job_id: str, user=Depends(require_role("viewer"))):  # noqa: B008
    status = scan_jobs.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@app.websocket("/ws/scan/{job_id}")
async def websocket_scan(websocket: WebSocket, job_id: str, token: str | None = None):
    token = token or websocket.cookies.get(ACCESS_COOKIE)
    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    await scan_manager.connect(job_id, websocket)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # keep connection alive with status push
                status = scan_jobs.get(job_id)
                if status:
                    await scan_manager.broadcast(job_id, {"status": status.status, "progress": status.progress})
    except WebSocketDisconnect:
        await scan_manager.disconnect(job_id, websocket)
    except Exception:
        await scan_manager.disconnect(job_id, websocket)


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
