"""Interface generica de canal de notificacao."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class NotificationPayload:
    subject: str
    body_html: str
    body_text: str
    recipient: str


class NotificationChannel(Protocol):
    name: str
    enabled: bool

    async def send(self, payload: NotificationPayload) -> bool:
        """Retorna True se envio bem-sucedido."""
