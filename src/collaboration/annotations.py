"""
Lightweight multi-user annotations for products with tagging and sharing.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
db = DatabaseManager()

DEFAULT_TAGS = {"promising", "overpriced", "copy-us", "watch", "low-priority"}


@dataclass
class Annotation:
    product_id: int
    user_id: str
    note: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class AnnotationService:
    """In-memory + DB-backed annotations (DB persistence is stubbed for now)."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._store: Dict[int, List[Annotation]] = {}

    async def add_annotation(self, product_id: int, user_id: str, note: str, tags: Optional[List[str]] = None) -> Annotation:
        tags = tags or []
        filtered_tags = [t for t in tags if t in DEFAULT_TAGS]
        annotation = Annotation(product_id=product_id, user_id=user_id, note=note, tags=filtered_tags)
        async with self._lock:
            self._store.setdefault(product_id, []).append(annotation)
        logger.info("Annotation added by %s on product %s", user_id, product_id)
        return annotation

    async def list_annotations(self, product_id: int) -> List[Annotation]:
        async with self._lock:
            return list(self._store.get(product_id, []))

    async def share_insights(self, product_id: int) -> Dict[str, List[str]]:
        """
        Aggregate notes/tags to share with the team.
        """
        ann = await self.list_annotations(product_id)
        notes = [a.note for a in ann]
        tags: List[str] = []
        for a in ann:
            tags.extend(a.tags)
        return {"notes": notes, "tags": tags}
