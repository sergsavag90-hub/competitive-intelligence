import os
import logging
import requests

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.webhook = os.getenv("SLACK_WEBHOOK_URL")

    def send_message(self, channel: str, text: str = "", blocks=None, attachments=None):
        if not self.token and not self.webhook:
            logger.debug("Slack token/webhook not configured.")
            return False
        headers = {"Content-Type": "application/json"}
        payload = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments
        url = (
            "https://slack.com/api/chat.postMessage"
            if self.token
            else self.webhook
        )
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Slack send failed: %s", exc)
            return False
