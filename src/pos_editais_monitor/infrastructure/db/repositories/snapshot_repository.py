from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.domain.entities.snapshot import Snapshot
from pos_editais_monitor.infrastructure.db.models.snapshot import SnapshotModel


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_sha256(self, sha: str) -> Snapshot | None:
        stmt = select(SnapshotModel).where(SnapshotModel.sha256 == sha)
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        if not m:
            return None
        return Snapshot(
            id=m.id,
            edital_id=m.edital_id,
            fonte_id=m.fonte_id,
            url=m.url,
            http_status=m.http_status,
            content_type=m.content_type,
            sha256=m.sha256,
            bytes_size=m.bytes_size,
            storage_path=m.storage_path,
            capturado_em=m.created_at,
            parser_name=m.parser_name,
            parse_confidence=m.parse_confidence,
            headers=m.headers,
        )

    async def add(self, snap: Snapshot) -> Snapshot:
        m = SnapshotModel(
            id=snap.id,
            edital_id=snap.edital_id,
            fonte_id=snap.fonte_id,
            url=snap.url,
            http_status=snap.http_status,
            content_type=snap.content_type,
            sha256=snap.sha256,
            bytes_size=snap.bytes_size,
            storage_path=snap.storage_path,
            parser_name=snap.parser_name,
            parse_confidence=snap.parse_confidence,
            headers=snap.headers,
        )
        self._session.add(m)
        await self._session.flush()
        return snap
