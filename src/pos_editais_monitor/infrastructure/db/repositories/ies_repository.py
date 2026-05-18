from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.domain.entities.ies import IES
from pos_editais_monitor.infrastructure.db.models.ies import IESModel


class IESRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_codigo_emec(self, codigo: str) -> IES | None:
        stmt = select(IESModel).where(IESModel.codigo_emec == codigo)
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return m.to_entity() if m else None

    async def find_by_sigla_or_nome(self, q: str) -> IES | None:
        ql = q.strip().upper()
        stmt = select(IESModel).where((IESModel.sigla == ql) | (IESModel.nome.ilike(f"%{q}%")))
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return m.to_entity() if m else None

    async def list_elegiveis(self) -> list[IES]:
        stmt = select(IESModel).where(IESModel.ativa.is_(True), IESModel.gratuita.is_(True))
        return [m.to_entity() for m in (await self._session.execute(stmt)).scalars().all()]

    async def upsert(self, i: IES) -> IES:
        existing = await self.get_by_codigo_emec(i.codigo_emec)
        if existing:
            stmt = select(IESModel).where(IESModel.codigo_emec == i.codigo_emec)
            m = (await self._session.execute(stmt)).scalar_one()
            m.ativa = i.ativa
            m.gratuita = i.gratuita
            m.categoria_administrativa = i.categoria_administrativa
            m.organizacao_academica = i.organizacao_academica
            return m.to_entity()
        m = IESModel.from_entity(i)
        self._session.add(m)
        await self._session.flush()
        return m.to_entity()
