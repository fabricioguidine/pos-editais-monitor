from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.domain.entities.edital import Edital
from pos_editais_monitor.infrastructure.db.models.edital import EditalModel


class EditalRepository:
    """Repositorio de Edital. Operacoes assincronas."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, edital_id: UUID) -> Edital | None:
        m = await self._session.get(EditalModel, edital_id)
        return m.to_entity() if m else None

    async def get_by_canonical_hash(self, canonical_hash: str) -> Edital | None:
        stmt = select(EditalModel).where(EditalModel.canonical_hash == canonical_hash)
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return m.to_entity() if m else None

    async def find_near_simhash(
        self, simhash: int, hamming_max: int = 3
    ) -> list[Edital]:
        """Busca editais com simhash proximo. Implementacao naive (O(n))
        suficiente para o volume MVP (< 10k editais). v0.3: substituir por
        LSH em Redis ou tabelas particionadas por bits de prefixo."""
        stmt = select(EditalModel)
        rows: Sequence[EditalModel] = (await self._session.execute(stmt)).scalars().all()
        return [
            m.to_entity()
            for m in rows
            if _hamming(m.simhash, simhash) <= hamming_max
        ]

    async def upsert(self, edital: Edital) -> Edital:
        existing = await self.get_by_canonical_hash(edital.canonical_hash)
        if existing:
            # Atualiza campos mutaveis
            stmt = (
                select(EditalModel)
                .where(EditalModel.canonical_hash == edital.canonical_hash)
            )
            m = (await self._session.execute(stmt)).scalar_one()
            m.simhash = edital.simhash
            m.status = edital.status.value
            m.texto_resumo = edital.texto_resumo
            m.url_pdf = edital.url_pdf
            return m.to_entity()
        m = EditalModel.from_entity(edital)
        self._session.add(m)
        await self._session.flush()
        return m.to_entity()

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[Edital]:
        stmt = (
            select(EditalModel)
            .order_by(EditalModel.inscricao_ate.asc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [m.to_entity() for m in rows]


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
