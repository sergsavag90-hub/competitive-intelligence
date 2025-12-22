import logging
import os
import requests

logger = logging.getLogger(__name__)


class PagerDutyClient:
    def __init__(self, routing_key: str | None = None):
        self.routing_key = routing_key or os.getenv("PAGERDUTY_ROUTING_KEY")

    def trigger(self, summary: str, severity: str = "error", source: str = "ci-app"):
        if not self.routing_key:
            logger.debug("PagerDuty routing key not configured.")
            return False
        url = "https://events.pagerduty.com/v2/enqueue"
        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "severity": severity,
                "source": source,
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("PagerDuty trigger failed: %s", exc)
            return False
