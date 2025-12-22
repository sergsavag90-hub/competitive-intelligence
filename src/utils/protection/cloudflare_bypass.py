import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CloudflareBypass:
    """Minimal heuristics to detect CF challenge and apply headers/workarounds."""

    def is_protected(self, driver) -> bool:
        try:
            text = driver.page_source.lower()
            return "cloudflare" in text and ("checking your browser" in text or "challenge" in text)
        except Exception:
            return False

    def apply_headers(self, driver, headers: Optional[dict] = None):
        """Inject custom headers via CDP for Chrome-based drivers."""
        headers = headers or {
            "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="124"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows",
        }
        try:
            driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": headers})
        except Exception as exc:
            logger.debug("Failed to set CF headers: %s", exc)
