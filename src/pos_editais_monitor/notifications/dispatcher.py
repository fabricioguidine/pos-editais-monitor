"""Dispatcher — agrupa matches do dia em digest, renderiza, envia.

Politica:
- Um envio por subscriber por dia (idempotente por `MatchRecord.notified`).
- Se `PEM_NOTIFY_ONLY_ON_MATCH` e nao ha matches, NAO envia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import Edital
from pos_editais_monitor.domain.entities.subscriber import SubscriberProfile
from pos_editais_monitor.notifications.channels.base import (
    NotificationChannel,
    NotificationPayload,
)
from pos_editais_monitor.notifications.channels.email import EmailChannel
from pos_editais_monitor.notifications.channels.telegram import TelegramChannel

log = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(slots=True)
class DigestItem:
    titulo: str
    ies_nome: str
    nivel_label: str
    modalidade_label: str
    area_label: str
    prazo: str | None
    url_origem: str
    url_pdf: str | None
    score: float


class NotificationDispatcher:
    def __init__(
        self,
        settings: Settings | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._channels: list[NotificationChannel] = channels or [
            EmailChannel(self._settings),
            TelegramChannel(self._settings),
        ]
        self._env = Environment(
            loader=FileSystemLoader(_TEMPLATES_DIR),
            autoescape=select_autoescape(["html", "xml", "j2"]),
        )

    async def send_digest(
        self,
        *,
        profile: SubscriberProfile,
        items: list[DigestItem],
    ) -> bool:
        if not items and self._settings.notify_only_on_match:
            log.info("digest_skipped_no_matches", profile=profile.nome)
            return False

        today = date.today().isoformat()
        ctx = {"data": today, "matches": items, "profile_name": profile.nome}
        html = self._env.get_template("digest.html.j2").render(**ctx)
        text = self._env.get_template("digest.txt.j2").render(**ctx)

        subject = f"[pos-editais] {len(items)} novo(s) edital(is) — {today}"
        recipient = profile.email or str(self._settings.notify_to)
        payload = NotificationPayload(
            subject=subject,
            body_html=html,
            body_text=text,
            recipient=recipient,
        )

        any_ok = False
        for ch in self._channels:
            if ch.enabled:
                if await ch.send(payload):
                    any_ok = True
        return any_ok

    @staticmethod
    def build_item(edital: Edital, ies_nome: str, area_label: str, score: float) -> DigestItem:
        return DigestItem(
            titulo=edital.titulo,
            ies_nome=ies_nome,
            nivel_label=edital.nivel.value.replace("_", " ").title(),
            modalidade_label=edital.modalidade.value.title(),
            area_label=area_label,
            prazo=(
                edital.periodo_inscricao.ate.isoformat()
                if edital.periodo_inscricao and edital.periodo_inscricao.ate
                else None
            ),
            url_origem=edital.url_origem,
            url_pdf=edital.url_pdf,
            score=score,
        )
