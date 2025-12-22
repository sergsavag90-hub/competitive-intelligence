import json
import os
import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """
    Simple 2Captcha / AntiCaptcha solver client.
    Supports reCAPTCHA v2/v3 and hCaptcha via external API.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "2captcha", timeout: int = 120):
        self.api_key = api_key or os.getenv("CAPTCHA_API_KEY", "")
        self.provider = provider
        self.timeout = timeout
        if not self.api_key:
            logger.warning("CAPTCHA_API_KEY not set; solver will be disabled.")

    def detect(self, driver) -> bool:
        """Naive detection of captcha widgets on page."""
        try:
            return (
                "captcha" in driver.page_source.lower()
                or "g-recaptcha" in driver.page_source.lower()
                or "h-captcha" in driver.page_source.lower()
            )
        except Exception:
            return False

    def get_site_key(self, driver) -> Optional[str]:
        """Extract sitekey from common recaptcha/hcaptcha widgets."""
        try:
            elems = driver.find_elements("css selector", "[data-sitekey]")
            if elems:
                return elems[0].get_attribute("data-sitekey")
        except Exception:
            pass
        return None

    def solve(self, site_key: str, url: str) -> Optional[str]:
        """Submit captcha to provider and poll for solution."""
        if not self.api_key:
            return None

        if self.provider == "2captcha":
            submit_url = "http://2captcha.com/in.php"
            params = {"key": self.api_key, "method": "userrecaptcha", "googlekey": site_key, "pageurl": url, "json": 1}
            resp = requests.post(submit_url, data=params, timeout=15)
            resp.raise_for_status()
            task_id = resp.json().get("request")
            if not task_id:
                return None
            return self._poll_2captcha(task_id)

        # AntiCaptcha placeholder (similar API)
        return None

    def _poll_2captcha(self, task_id: str) -> Optional[str]:
        result_url = "http://2captcha.com/res.php"
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            time.sleep(5)
            resp = requests.get(result_url, params={"key": self.api_key, "action": "get", "id": task_id, "json": 1}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == 1:
                return data.get("request")
        logger.error("Captcha solve timeout for task %s", task_id)
        return None

    def submit_solution(self, driver, solution: str) -> bool:
        """Inject solution token into page."""
        try:
            script = """
                document.querySelectorAll('textarea[name="g-recaptcha-response"], #g-recaptcha-response')
                    .forEach(el => {el.value = '%s'; el.innerHTML = '%s';});
            """ % (solution, solution)
            driver.execute_script(script)
            return True
        except Exception as exc:
            logger.error("Failed to submit captcha solution: %s", exc)
            return False
