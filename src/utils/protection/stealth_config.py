import logging
import random
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class StealthConfigurator:
    """Applies stealth tweaks to Selenium driver."""

    def __init__(self, user_agent_rotation: bool = True):
        self.user_agent_rotation = user_agent_rotation

    def _get_user_agent(self) -> Optional[str]:
        if not self.user_agent_rotation:
            return None
        try:
            resp = requests.get("https://useragentstring.com/pages/api.php?typ=browser&amount=20", timeout=10)
            if resp.ok:
                agents = [ua.strip() for ua in resp.text.split("\n") if ua.strip()]
                if agents:
                    return random.choice(agents)
        except Exception:
            pass
        return None

    def apply(self, driver):
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        window.navigator.chrome = { runtime: {} };
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                    """
                },
            )
            ua = self._get_user_agent()
            if ua:
                driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": ua})
        except Exception as exc:
            logger.debug("Stealth configuration failed: %s", exc)
