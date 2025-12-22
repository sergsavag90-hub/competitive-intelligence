import logging
import os
from typing import Optional

from .captcha_solver import CaptchaSolver
from .proxy_manager import ProxyManager
from .stealth_config import StealthConfigurator
from .cloudflare_bypass import CloudflareBypass

logger = logging.getLogger(__name__)


class ProtectionBypassManager:
    """Coordinates captcha solving, proxy rotation, stealth tweaks, and Cloudflare headers."""

    def __init__(self):
        self.captcha = CaptchaSolver(
            api_key=os.getenv("CAPTCHA_API_KEY"),
            provider=os.getenv("CAPTCHA_PROVIDER", "2captcha"),
            timeout=int(os.getenv("CAPTCHA_TIMEOUT", "120")),
        )
        self.proxy = ProxyManager(
            provider=os.getenv("PROXY_PROVIDER", "brightdata"),
            rotation_interval_minutes=int(os.getenv("PROXY_ROTATION_MIN", "5")),
            geo_targets=(os.getenv("PROXY_GEO") or "").split(","),
        )
        self.stealth = StealthConfigurator(user_agent_rotation=True)
        self.cf = CloudflareBypass()

    def configure_driver(self, driver, url: str):
        if self.cf.is_protected(driver):
            self.cf.apply_headers(driver)
        if self.proxy.is_needed(url):
            proxy = self.proxy.get_residential_proxy()
            if proxy:
                self._apply_proxy(driver, proxy)
        self.stealth.apply(driver)
        return driver

    def _apply_proxy(self, driver, proxy: str):
        # Basic proxy injection via CDP for Chrome; for full support, recreate driver with proxy settings.
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {"Proxy": proxy}})
            logger.debug("Applied proxy %s", proxy)
        except Exception as exc:
            logger.debug("Could not apply proxy %s: %s", proxy, exc)

    def solve_captcha_if_present(self, driver) -> bool:
        if self.captcha.detect(driver):
            site_key = self.captcha.get_site_key(driver)
            if not site_key:
                return False
            solution = self.captcha.solve(site_key, driver.current_url)
            if solution:
                return self.captcha.submit_solution(driver, solution)
        return False
