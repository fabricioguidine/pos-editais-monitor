"""Rate limiter token-bucket distribuido via Redis.

Funciona entre workers, garante limite por host. Em ambientes sem Redis,
cai para implementacao em-memoria por processo.
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlparse

from redis.asyncio import Redis

from pos_editais_monitor.core.logging import get_logger

log = get_logger(__name__)

# Lua script atomico: tenta consumir 1 token, retorna ms-to-wait (0 se ok).
_LUA_TOKEN_BUCKET = """
local key = KEYS[1]
local rate = tonumber(ARGV[1])         -- tokens por segundo
local capacity = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local cost = 1

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local ts = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  ts = now_ms
end

local delta_ms = math.max(0, now_ms - ts)
tokens = math.min(capacity, tokens + delta_ms * rate / 1000.0)

local wait_ms = 0
if tokens >= cost then
  tokens = tokens - cost
else
  wait_ms = math.ceil((cost - tokens) * 1000.0 / rate)
end

redis.call('HMSET', key, 'tokens', tokens, 'ts', now_ms)
redis.call('PEXPIRE', key, 60000)
return wait_ms
"""


class RateLimiter:
    """Token bucket por host. Aguarda ate ter token disponivel."""

    def __init__(self, redis: Redis | None, rps: float, capacity: int = 5) -> None:
        self._redis = redis
        self._rps = rps
        self._capacity = capacity
        self._fallback_state: dict[str, tuple[float, float]] = {}  # host -> (tokens, last_ts)
        self._fallback_lock = asyncio.Lock()

    async def acquire(self, url: str) -> None:
        host = urlparse(url).hostname or "unknown"
        if self._redis is None:
            await self._acquire_local(host)
            return
        await self._acquire_redis(host)

    async def _acquire_redis(self, host: str) -> None:
        key = f"pem:ratelimit:{host}"
        while True:
            now_ms = int(time.time() * 1000)
            wait_ms = await self._redis.eval(
                _LUA_TOKEN_BUCKET, 1, key, self._rps, self._capacity, now_ms
            )
            if wait_ms == 0:
                return
            log.debug("rate_limit_wait", host=host, wait_ms=int(wait_ms))
            await asyncio.sleep(wait_ms / 1000.0)

    async def _acquire_local(self, host: str) -> None:
        async with self._fallback_lock:
            tokens, last_ts = self._fallback_state.get(host, (float(self._capacity), time.time()))
            now = time.time()
            tokens = min(self._capacity, tokens + (now - last_ts) * self._rps)
            if tokens < 1.0:
                wait = (1.0 - tokens) / self._rps
                self._fallback_state[host] = (0.0, now + wait)
                await asyncio.sleep(wait)
                self._fallback_state[host] = (0.0, time.time())
            else:
                self._fallback_state[host] = (tokens - 1.0, now)
