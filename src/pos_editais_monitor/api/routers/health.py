from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from pos_editais_monitor import __version__
from pos_editais_monitor.api.schemas.common import HealthResponse
from pos_editais_monitor.infrastructure.cache.redis_client import get_redis
from pos_editais_monitor.infrastructure.db.session import _ensure_initialized

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse, summary="Liveness")
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@router.get("/readyz", response_model=HealthResponse, summary="Readiness (db+redis)")
async def readyz() -> HealthResponse:
    components: dict[str, str] = {}
    try:
        factory = _ensure_initialized()
        async with factory() as s:
            await s.execute(text("SELECT 1"))
        components["postgres"] = "ok"
    except Exception as exc:
        components["postgres"] = f"error: {exc}"
    try:
        r = get_redis()
        await r.ping()
        components["redis"] = "ok"
    except Exception as exc:
        components["redis"] = f"error: {exc}"

    status = "ok" if all(v == "ok" for v in components.values()) else "degraded"
    return HealthResponse(status=status, version=__version__, components=components)
