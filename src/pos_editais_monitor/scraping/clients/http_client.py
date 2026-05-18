"""HTTP client async resiliente: rate limit + robots + retry + circuit breaker.

Implementacao deliberadamente coesa: aplica todos os middlewares em ordem
fixa. Spider nao precisa orquestrar nada — chama `client.fetch(req)`.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from redis.asyncio import Redis
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.core.observability import METRICS
from pos_editais_monitor.scraping.errors import (
    CircuitOpenError,
    RateLimitedError,
    RobotsDisallowedError,
)
from pos_editais_monitor.scraping.middlewares import (
    CircuitBreaker,
    RateLimiter,
    RobotsChecker,
)
from pos_editais_monitor.scraping.types import FetchRequest, RawResponse

log = get_logger(__name__)


_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
_RETRYABLE_EXCEPTIONS = (
    httpx.TransportError,
    httpx.TimeoutException,
    RateLimitedError,
)


class HttpClient:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        redis: Redis | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._redis = redis
        self._client = httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            timeout=httpx.Timeout(self._settings.http_timeout_seconds),
            headers={
                "User-Agent": self._settings.http_user_agent,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.6",
            },
        )
        self._rate = RateLimiter(redis=redis, rps=self._settings.rate_limit_rps)
        self._cb = CircuitBreaker()
        self._robots = RobotsChecker(user_agent=self._settings.http_user_agent)

    async def aclose(self) -> None:
        await self._client.aclose()

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator["HttpClient"]:
        try:
            yield self
        finally:
            await self.aclose()

    async def fetch(self, req: FetchRequest) -> RawResponse:
        self._cb.check(req.url)
        if self._settings.respect_robots:
            await self._robots.assert_allowed(req.url, self._client)
        await self._rate.acquire(req.url)

        start = time.perf_counter()
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._settings.http_max_retries),
                wait=wait_exponential_jitter(initial=1.0, max=30.0, jitter=1.0),
                retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
                reraise=True,
            ):
                with attempt:
                    resp = await self._client.request(
                        req.method,
                        req.url,
                        headers=req.headers or None,
                        content=req.body,
                    )
                    if resp.status_code in _RETRYABLE_STATUS:
                        if resp.status_code == 429:
                            raise RateLimitedError(req.url)
                        resp.raise_for_status()
        except (RetryError, RobotsDisallowedError, CircuitOpenError):
            self._cb.record_failure(req.url)
            METRICS.spider_requests_total.labels(req.spider, "error").inc()
            raise
        except httpx.HTTPError:
            self._cb.record_failure(req.url)
            METRICS.spider_requests_total.labels(req.spider, "error").inc()
            raise
        latency = time.perf_counter() - start
        self._cb.record_success(req.url)
        METRICS.spider_request_latency_seconds.labels(req.spider).observe(latency)
        METRICS.spider_requests_total.labels(req.spider, str(resp.status_code)).inc()
        log.debug(
            "http_fetched",
            url=req.url,
            status=resp.status_code,
            bytes=len(resp.content),
            latency_ms=int(latency * 1000),
            spider=req.spider,
        )
        return RawResponse(
            url=req.url,
            final_url=str(resp.url),
            status=resp.status_code,
            headers={k.lower(): v for k, v in resp.headers.items()},
            body=resp.content,
            via="httpx",
            spider=req.spider,
        )
