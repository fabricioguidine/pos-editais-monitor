"""RSS auto-detect: dado um HTML, descobre se ha feed disponivel.

Estrategia em ordem:
1. Procura <link rel="alternate" type="application/rss+xml"> no <head>
2. Tenta paths comuns: /feed/, /feed, /rss, /rss.xml
3. Cache por host para evitar reprobing
"""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from pos_editais_monitor.core.logging import get_logger

log = get_logger(__name__)

_COMMON_PATHS = ("/feed/", "/feed", "/rss", "/rss.xml", "/?feed=rss2")


class RSSDetector:
    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    def from_html(self, base_url: str, html: str) -> str | None:
        """Extrai <link rel='alternate' type='*rss*'> ou '*atom*'."""
        tree = HTMLParser(html)
        for node in tree.css("link[rel=alternate]"):
            t = (node.attributes.get("type") or "").lower()
            if "rss" in t or "atom" in t:
                href = node.attributes.get("href")
                if href:
                    return urljoin(base_url, href)
        return None

    async def probe(self, base_url: str, client: httpx.AsyncClient) -> str | None:
        """Probe paths conhecidos. Cacheado por host."""
        if base_url in self._cache:
            return self._cache[base_url]
        for path in _COMMON_PATHS:
            candidate = urljoin(base_url, path)
            try:
                resp = await client.head(candidate, timeout=8.0, follow_redirects=True)
                if resp.status_code == 200 and self._looks_like_feed(resp.headers):
                    log.info("rss_detected", base=base_url, url=candidate)
                    self._cache[base_url] = candidate
                    return candidate
            except httpx.HTTPError as exc:
                log.debug("rss_probe_fail", url=candidate, err=str(exc))
        self._cache[base_url] = None
        return None

    @staticmethod
    def _looks_like_feed(headers: httpx.Headers) -> bool:
        ct = headers.get("content-type", "").lower()
        return any(k in ct for k in ("xml", "rss", "atom"))
