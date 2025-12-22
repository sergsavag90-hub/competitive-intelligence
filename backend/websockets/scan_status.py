import asyncio
from typing import Dict, Set

from fastapi import WebSocket


class ScanStatusManager:
    """Simple WebSocket manager for scan status streaming."""

    def __init__(self) -> None:
        self.connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.connections.setdefault(job_id, set()).add(websocket)

    async def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self.connections.get(job_id)
            if conns and websocket in conns:
                conns.remove(websocket)
            if conns and len(conns) == 0:
                self.connections.pop(job_id, None)

    async def broadcast(self, job_id: str, message: Dict) -> None:
        async with self._lock:
            conns = list(self.connections.get(job_id, []))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                # Best-effort; connection might be closed elsewhere
                pass
