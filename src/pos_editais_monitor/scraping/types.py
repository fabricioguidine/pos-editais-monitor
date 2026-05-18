"""Tipos comuns do layer de scraping."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pos_editais_monitor.core.utils import utcnow


@dataclass(slots=True)
class FetchRequest:
    url: str
    method: Literal["GET", "POST"] = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    timeout_seconds: int | None = None
    allow_playwright: bool = False     # spider opta por permitir fallback
    spider: str = ""


@dataclass(slots=True)
class RawResponse:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    body: bytes
    fetched_at: datetime = field(default_factory=utcnow)
    via: Literal["httpx", "playwright", "cache"] = "httpx"
    spider: str = ""

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()

    @property
    def is_html(self) -> bool:
        return "html" in self.content_type

    @property
    def is_pdf(self) -> bool:
        return self.content_type == "application/pdf"

    @property
    def is_xml_or_rss(self) -> bool:
        ct = self.content_type
        return "xml" in ct or "rss" in ct or "atom" in ct

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")
