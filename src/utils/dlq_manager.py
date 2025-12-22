import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import redis

from src.utils.config import config


class DeadLetterQueue:
    """Redis-backed DLQ for failed scrape jobs."""

    def __init__(self, redis_url: Optional[str] = None, list_name: str = "scrape_dlq"):
        self.redis_url = redis_url or os.getenv("REDIS_URL") or config.redis.get("url") if getattr(config, "redis", None) else None
        self.list_name = list_name
        self.client = redis.from_url(self.redis_url) if self.redis_url else None

    def add(self, payload: Dict) -> None:
        if not self.client:
            return
        enriched = {
            **payload,
            "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
        }
        self.client.lpush(self.list_name, json.dumps(enriched))

    def fetch(self, count: int = 50) -> List[Dict]:
        if not self.client:
            return []
        items = self.client.lrange(self.list_name, 0, count - 1)
        return [json.loads(item) for item in items]

    def requeue(self, url: str) -> None:
        if not self.client:
            return
        # remove one occurrence of url entry
        entries = self.fetch(1000)
        for entry in entries:
            if entry.get("url") == url:
                self.client.lrem(self.list_name, 1, json.dumps(entry))
                break
