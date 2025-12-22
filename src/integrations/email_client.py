import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class EmailClient:
    def __init__(self, host: str | None = None, port: int | None = None, username: str | None = None, password: str | None = None):
        self.host = host or os.getenv("SMTP_HOST")
        self.port = int(port or os.getenv("SMTP_PORT", "587"))
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.sender = os.getenv("SMTP_FROM", self.username or "noreply@example.com")

    def send_html(self, recipients: list[str], subject: str, html: str):
        if not self.host or not self.username or not self.password:
            logger.debug("SMTP not configured.")
            return False
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ",".join(recipients)
        msg.attach(MIMEText(html, "html"))
        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, recipients, msg.as_string())
            return True
        except Exception as exc:
            logger.error("Email send failed: %s", exc)
            return False
