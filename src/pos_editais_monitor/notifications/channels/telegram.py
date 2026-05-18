"""Canal Telegram (opcional, secundario)."""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ParseMode

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.core.observability import METRICS
from pos_editais_monitor.notifications.channels.base import NotificationPayload

log = get_logger(__name__)


class TelegramChannel:
    name = "telegram"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._bot: Bot | None = None

    @property
    def enabled(self) -> bool:
        return (
            self._settings.telegram_enabled
            and bool(self._settings.telegram_bot_token.get_secret_value())
            and bool(self._settings.telegram_chat_id)
        )

    def _get_bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(
                token=self._settings.telegram_bot_token.get_secret_value(),
            )
        return self._bot

    async def send(self, payload: NotificationPayload) -> bool:
        if not self.enabled:
            return False
        try:
            await self._get_bot().send_message(
                chat_id=self._settings.telegram_chat_id,
                text=payload.body_text[:4000],
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
        except Exception as exc:
            log.error("telegram_send_failed", err=str(exc))
            METRICS.notifications_sent_total.labels(self.name, "error").inc()
            return False
        METRICS.notifications_sent_total.labels(self.name, "ok").inc()
        return True
