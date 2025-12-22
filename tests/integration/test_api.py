import pytest
from httpx import AsyncClient

from backend.fastapi_app import app


@pytest.mark.asyncio
async def test_api_health_competitors_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/competitors")
        assert resp.status_code in (401, 403)
