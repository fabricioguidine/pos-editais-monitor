"""Engine e session factory assincrona."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pos_editais_monitor.core.config import get_settings


def create_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        future=True,
    )
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine, session_factory


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _ensure_initialized() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    if _session_factory is None:
        _engine, _session_factory = create_engine_and_session()
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Context manager async. Commit em sucesso, rollback em excecao."""
    factory = _ensure_initialized()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
