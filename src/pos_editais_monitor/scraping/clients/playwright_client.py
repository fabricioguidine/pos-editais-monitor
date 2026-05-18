"""Playwright pool. Lazy init. Usado apenas em sites JS-heavy."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.scraping.types import RawResponse

log = get_logger(__name__)


class PlaywrightClient:
    """Pool simples de browser contexts. Pool de 2 por default (configuravel)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._semaphore = asyncio.Semaphore(self._settings.playwright_pool_size)
        self._lock = asyncio.Lock()

    async def _ensure_started(self) -> Browser:
        async with self._lock:
            if self._browser is None:
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(
                    headless=self._settings.playwright_headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                log.info("playwright_started")
        assert self._browser is not None
        return self._browser

    async def aclose(self) -> None:
        async with self._lock:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            if self._pw is not None:
                await self._pw.stop()
                self._pw = None
                log.info("playwright_stopped")

    @asynccontextmanager
    async def _context(self) -> AsyncIterator[BrowserContext]:
        await self._semaphore.acquire()
        try:
            browser = await self._ensure_started()
            ctx = await browser.new_context(
                user_agent=self._settings.http_user_agent,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
            )
            try:
                yield ctx
            finally:
                await ctx.close()
        finally:
            self._semaphore.release()

    async def fetch(self, url: str, *, spider: str = "") -> RawResponse:
        async with self._context() as ctx:
            page = await ctx.new_page()
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=15000)
                html = await page.content()
                status = response.status if response else 0
                final_url = page.url
                return RawResponse(
                    url=url,
                    final_url=final_url,
                    status=status,
                    headers={"content-type": "text/html; charset=utf-8"},
                    body=html.encode("utf-8"),
                    via="playwright",
                    spider=spider,
                )
            finally:
                await page.close()
