from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.infrastructure.db.session import _ensure_initialized


async def db_session() -> AsyncIterator[AsyncSession]:
    factory = _ensure_initialized()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.api_key.get_secret_value()
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )
