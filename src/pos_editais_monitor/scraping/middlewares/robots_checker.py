"""Verificador de robots.txt usando protego."""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse

import httpx
from protego import Protego

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.scraping.errors import RobotsDisallowedError

log = get_logger(__name__)


class RobotsChecker:
    def __init__(self, user_agent: str, cache_ttl_seconds: int = 24 * 3600) -> None:
        self._ua = user_agent
        self._ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[Protego | None, float]] = {}

    async def assert_allowed(self, url: str, client: httpx.AsyncClient) -> None:
        host = urlparse(url).hostname or ""
        parsed = await self._fetch(host, url, client)
        if parsed is None:
            return    # robots.txt nao encontrado / inacessivel - permitido por default
        if not parsed.can_fetch(url, self._ua):
            log.info("robots_disallowed", url=url, ua=self._ua)
            raise RobotsDisallowedError(f"robots.txt disallows {url}")

    async def _fetch(
        self, host: str, url: str, client: httpx.AsyncClient
    ) -> Protego | None:
        cached = self._cache.get(host)
        if cached and time.time() - cached[1] < self._ttl:
            return cached[0]
        scheme = urlparse(url).scheme or "https"
        robots_url = urljoin(f"{scheme}://{host}/", "/robots.txt")
        try:
            resp = await client.get(robots_url, timeout=10.0, follow_redirects=True)
        except Exception as exc:
            log.debug("robots_fetch_fail", host=host, err=str(exc))
            self._cache[host] = (None, time.time())
            return None
        if resp.status_code != 200 or not resp.text:
            self._cache[host] = (None, time.time())
            return None
        parsed = Protego.parse(resp.text)
        self._cache[host] = (parsed, time.time())
        return parsed
