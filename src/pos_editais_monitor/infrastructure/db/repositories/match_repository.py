from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.core.utils import utcnow
from pos_editais_monitor.infrastructure.db.models.match_record import MatchRecordModel


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        subscriber_id: UUID,
        edital_id: UUID,
        score: float,
        explanation: dict,
    ) -> MatchRecordModel:
        m = MatchRecordModel(
            subscriber_id=subscriber_id,
            edital_id=edital_id,
            score=score,
            explanation_json=explanation,
        )
        self._session.add(m)
        await self._session.flush()
        return m

    async def pending_notifications_for(
        self, subscriber_id: UUID, since_hours: int = 24
    ) -> list[MatchRecordModel]:
        since = utcnow() - timedelta(hours=since_hours)
        stmt = (
            select(MatchRecordModel)
            .where(
                MatchRecordModel.subscriber_id == subscriber_id,
                MatchRecordModel.notified.is_(False),
                MatchRecordModel.created_at >= since,
            )
            .order_by(MatchRecordModel.score.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def mark_notified(self, ids: list[UUID]) -> None:
        from sqlalchemy import update

        stmt = (
            update(MatchRecordModel)
            .where(MatchRecordModel.id.in_(ids))
            .values(notified=True, notified_at=utcnow())
        )
        await self._session.execute(stmt)
