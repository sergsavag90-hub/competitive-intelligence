"""
Abstraction over vector DB (Pinecone/Weaviate). Defaults to in-memory if client not configured.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:  # Optional dependency
    import pinecone
except Exception:  # pragma: no cover - optional
    pinecone = None


class VectorStore:
    def __init__(self, index_name: str = "ci-insights", api_key: Optional[str] = None, environment: Optional[str] = None):
        self.index_name = index_name
        self.api_key = api_key
        self.environment = environment
        self._mem: List[Dict] = []

        if pinecone and api_key:
            pinecone.init(api_key=api_key, environment=environment or "us-east-1")
            self.index = pinecone.Index(index_name)
        else:
            self.index = None
            if not api_key:
                logger.info("VectorStore running in in-memory mode (no Pinecone API key).")

    def upsert(self, vectors: List[Dict]) -> None:
        if self.index:
            self.index.upsert(vectors=vectors)
        else:
            self._mem.extend(vectors)

    def query(self, vector: List[float], top_k: int = 5) -> List[Dict]:
        if self.index:
            res = self.index.query(vector=vector, top_k=top_k, include_metadata=True)
            return res.get("matches", [])
        # naive in-memory placeholder
        return self._mem[:top_k]
