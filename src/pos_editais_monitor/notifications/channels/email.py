"""Canal Email via aiosmtplib (async).

Suporta STARTTLS (Gmail App Password). Em dev, aponta para smtp4dev no
docker-compose (porta 2525, sem TLS) — todas as mensagens ficam visiveis em
http://localhost:5000.
"""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.core.observability import METRICS
from pos_editais_monitor.notifications.channels.base import NotificationPayload

log = get_logger(__name__)


class EmailChannel:
    name = "email"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.email_enabled

    async def send(self, payload: NotificationPayload) -> bool:
        if not self.enabled:
            log.info("email_disabled")
            return False

        msg = EmailMessage()
        msg["From"] = str(self._settings.smtp_from or self._settings.smtp_username)
        msg["To"] = payload.recipient
        msg["Subject"] = payload.subject
        msg.set_content(payload.body_text)
        msg.add_alternative(payload.body_html, subtype="html")

        try:
            use_tls = self._settings.smtp_port == 465
            start_tls = self._settings.smtp_port == 587
            await aiosmtplib.send(
                msg,
                hostname=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_username or None,
                password=(
                    self._settings.smtp_password.get_secret_value()
                    if self._settings.smtp_password.get_secret_value()
                    else None
                ),
                use_tls=use_tls,
                start_tls=start_tls,
                timeout=30,
            )
        except Exception as exc:
            log.error("email_send_failed", err=str(exc), to=payload.recipient)
            METRICS.notifications_sent_total.labels(self.name, "error").inc()
            return False
        log.info("email_sent", to=payload.recipient, subject=payload.subject[:80])
        METRICS.notifications_sent_total.labels(self.name, "ok").inc()
        return True
