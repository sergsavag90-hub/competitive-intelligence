import logging
from typing import Dict, Any, List, Optional

from src.integrations.slack_client import SlackClient
from src.integrations.telegram_client import TelegramClient
from src.integrations.email_client import EmailClient
from src.integrations.webhook_client import WebhookClient
from src.integrations.pagerduty_client import PagerDutyClient
from src.integrations.rules_engine import RulesEngine

logger = logging.getLogger(__name__)


class NotificationManager:
    """Route alerts to Slack, Telegram, Email, Webhook, PagerDuty based on rules."""

    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None):
        self.slack = SlackClient()
        self.telegram = TelegramClient()
        self.email = EmailClient()
        self.webhook_url = None
        self.webhook = None
        self.pagerduty = PagerDutyClient()
        self.rules_engine = RulesEngine(rules)

    def configure_webhook(self, url: str):
        self.webhook_url = url
        self.webhook = WebhookClient(url)

    async def send_price_alert(self, user: Dict[str, Any], product: Dict[str, Any], old_price: float, new_price: float):
        change = (new_price - old_price) / old_price if old_price else 0
        context = {"change": change, "product": product}
        triggered = self.rules_engine.evaluate(context)
        for rule in triggered:
            actions = rule.get("actions", [])
            for action in actions:
                self._dispatch(action, user, product, change)

    def _dispatch(self, action: Dict[str, Any], user: Dict[str, Any], product: Dict[str, Any], change: float):
        atype = action.get("type")
        if atype == "slack" and user.get("slack_channel"):
            blocks = self._build_slack_blocks(product, change)
            self.slack.send_message(user["slack_channel"], text="", blocks=blocks)
        elif atype == "telegram" and user.get("telegram_chat_id"):
            self.telegram.send_message(user["telegram_chat_id"], f"Price alert: {product.get('name')} {change:.1%}")
        elif atype == "email" and action.get("recipients"):
            html = f"<h3>Price alert</h3><p>{product.get('name')}: {change:.1%}</p>"
            self.email.send_html(action["recipients"], "Price Alert", html)
        elif atype == "webhook" and self.webhook:
            payload = {"product": product, "change": change}
            self.webhook.send(payload)
        elif atype == "pagerduty":
            self.pagerduty.trigger(f"Critical price change {change:.1%} for {product.get('name')}")

    def _build_slack_blocks(self, product: Dict[str, Any], change: float):
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Price Alert:* {product.get('name')}"},
                "fields": [
                    {"type": "mrkdwn", "text": f"*Change:* {change:.1%}"},
                    {"type": "mrkdwn", "text": f"*Link:* {product.get('url', '')}"},
                ],
            }
        ]
