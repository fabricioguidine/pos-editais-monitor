from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.domain.entities.fonte import Fonte
from pos_editais_monitor.infrastructure.db.models.fonte import FonteModel


class FonteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_codigo(self, codigo: str) -> Fonte | None:
        stmt = select(FonteModel).where(FonteModel.codigo == codigo)
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return m.to_entity() if m else None

    async def list_active(self) -> list[Fonte]:
        stmt = select(FonteModel).where(FonteModel.ativa.is_(True))
        return [m.to_entity() for m in (await self._session.execute(stmt)).scalars().all()]

    async def upsert(self, f: Fonte) -> Fonte:
        existing = await self.get_by_codigo(f.codigo)
        if existing:
            return existing
        m = FonteModel.from_entity(f)
        self._session.add(m)
        await self._session.flush()
        return m.to_entity()
