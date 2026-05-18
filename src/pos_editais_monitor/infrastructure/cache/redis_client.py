"""Redis async singleton."""

from __future__ import annotations

from redis.asyncio import Redis

from pos_editais_monitor.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            get_settings().redis_url,
            decode_responses=False,
            encoding="utf-8",
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
