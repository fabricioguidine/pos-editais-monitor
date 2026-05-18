"""Dead-letter queue em Redis.

Itens que falham consistentemente em algum stage acabam aqui. Operacao
manual pode reprocessar via CLI: `pem dead-letter replay`.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from pos_editais_monitor.core.logging import get_logger

log = get_logger(__name__)
_DLQ_KEY = "pem:dlq"


class DeadLetterQueue:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def push(self, stage: str, reason: str, payload: dict[str, Any]) -> None:
        entry = {"stage": stage, "reason": reason, "payload": payload}
        await self._redis.lpush(_DLQ_KEY, json.dumps(entry, default=str))
        log.warning("dead_letter_pushed", stage=stage, reason=reason)

    async def pop_one(self) -> dict[str, Any] | None:
        raw = await self._redis.rpop(_DLQ_KEY)
        if not raw:
            return None
        return json.loads(raw)

    async def size(self) -> int:
        return await self._redis.llen(_DLQ_KEY)
