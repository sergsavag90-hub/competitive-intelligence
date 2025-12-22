import logging
import requests

logger = logging.getLogger(__name__)


class WebhookClient:
    def __init__(self, url: str):
        self.url = url

    def send(self, payload: dict):
        try:
            resp = requests.post(self.url, json=payload, timeout=5)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Webhook send failed: %s", exc)
            return False
