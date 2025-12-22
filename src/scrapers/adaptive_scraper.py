"""
Adaptive scraper that:
- Classifies page type to pick strategy.
- Auto-detects product selectors (self-healing).
- Adjusts rate limits based on response time/success.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from src.ml.page_classifier import PageClassifier
from src.utils.selector_detector import detect_product_selectors
from src.utils.selenium_helper import SeleniumHelper
from src.utils.config import config

logger = logging.getLogger(__name__)


DEFAULT_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
]


class AdaptiveScraper:
    """Combines classifier, selector detection, and adaptive pacing."""

    def __init__(
        self,
        helper: Optional[SeleniumHelper] = None,
        classifier: Optional[PageClassifier] = None,
        user_agents: Optional[List[str]] = None,
    ):
        self.helper = helper or SeleniumHelper()
        self.classifier = classifier or PageClassifier()
        self.user_agents = user_agents or getattr(config, "user_agent_pool", None) or DEFAULT_UA_POOL
        self.ua_index = 0
        self.delay = 0.5
        self.min_delay = 0.2
        self.max_delay = 5.0

    async def scrape(self, url: str) -> Dict[str, Any]:
        """
        Fetch page, classify, detect selectors, and extract lightweight data.
        Returns a dict with page_type, selectors, and extracted products.
        """
        await asyncio.sleep(self.delay)
        start = time.monotonic()

        try:
            html = await self._fetch_page(url)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.exception("Adaptive scrape failed for %s", url)
            self._adjust_rate(response_time=5.0, success=False)
            return {"url": url, "error": str(exc)}

        response_time = max(time.monotonic() - start, 0.01)
        self._adjust_rate(response_time, success=True)

        page_type = self.classifier.predict(html)
        selectors = detect_product_selectors(html)
        products = self._extract_products(html, selectors)

        return {
            "url": url,
            "page_type": page_type,
            "selectors": selectors,
            "products": products,
            "response_time": response_time,
            "delay_used": self.delay,
        }

    async def scrape_many(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Sequential adaptive scraping across URLs."""
        results: List[Dict[str, Any]] = []
        for url in urls:
            results.append(await self.scrape(url))
        return results

    async def _fetch_page(self, url: str) -> str:
        """Fetch page source via Selenium helper with UA rotation."""
        ua = self._next_user_agent()
        async with self.helper.driver_context() as driver:
            try:
                if ua:
                    try:
                        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": ua})
                    except Exception:
                        pass
                driver.get(url)
                return driver.page_source
            finally:
                try:
                    self.helper._last_url = url  # noqa: SLF001
                except Exception:
                    pass

    def _next_user_agent(self) -> Optional[str]:
        if not self.user_agents:
            return None
        ua = self.user_agents[self.ua_index % len(self.user_agents)]
        self.ua_index += 1
        return ua

    def _adjust_rate(self, response_time: float, success: bool) -> None:
        """Adapt delay based on observed response time and success."""
        if not success:
            self.delay = min(self.max_delay, self.delay * 1.5)
            return
        if response_time > 4:
            self.delay = min(self.max_delay, self.delay * 1.3)
        elif response_time < 1:
            self.delay = max(self.min_delay, self.delay * 0.8)

    def _extract_products(self, html: str, selectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract minimal product data using detected selectors."""
        soup = BeautifulSoup(html or "", "html.parser")
        products: List[Dict[str, Any]] = []

        if not selectors:
            return products

        primary_selector = selectors[0]["selector"]
        for el in soup.select(primary_selector)[:200]:
            title_el = el.find(["h1", "h2", "h3", "h4", "h5"])
            price_el = el.find(text=True, recursive=True)
            img_el = el.find("img")
            products.append(
                {
                    "title": title_el.get_text(strip=True) if title_el else None,
                    "price_text": price_el.strip() if isinstance(price_el, str) else None,
                    "image": img_el.get("src") if img_el and img_el.has_attr("src") else None,
                    "url": el.find("a").get("href") if el.find("a") and el.find("a").has_attr("href") else None,
                }
            )

        return products
