import os
import random
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages rotation of residential proxies.
    Format: http://user:pass@host:port
    """

    def __init__(
        self,
        provider: str = "brightdata",
        rotation_interval_minutes: int = 5,
        geo_targets: Optional[List[str]] = None,
    ):
        self.provider = provider
        self.rotation_interval = rotation_interval_minutes * 60
        self.last_rotation = 0.0
        self.geo_targets = geo_targets or []
        self.pool = self._load_pool()

    def _load_pool(self) -> List[str]:
        # Expect list via env or config file
        raw = os.getenv("PROXY_POOL", "")
        pool = [p.strip() for p in raw.split(",") if p.strip()]
        if not pool:
            logger.warning("Proxy pool is empty; rotation disabled.")
        return pool

    def is_needed(self, url: str) -> bool:
        return True  # always rotate for now

    def get_residential_proxy(self) -> Optional[str]:
        now = time.time()
        if not self.pool:
            return None
        if now - self.last_rotation > self.rotation_interval:
            self.last_rotation = now
        proxy = random.choice(self.pool)
        return proxy
