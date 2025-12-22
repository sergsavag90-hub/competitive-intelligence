import os
import logging
import requests

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("TELEGRAM_TOKEN")

    def send_message(self, chat_id: str, text: str):
        if not self.token:
            logger.debug("Telegram token not configured.")
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Telegram send failed: %s", exc)
            return False
