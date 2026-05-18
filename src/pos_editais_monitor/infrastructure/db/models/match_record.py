from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from pos_editais_monitor.infrastructure.db.base import Base, TimestampMixin, gen_uuid


class MatchRecordModel(TimestampMixin, Base):
    __tablename__ = "match_records"
    __table_args__ = (
        Index("ix_match_subscriber_edital", "subscriber_id", "edital_id", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=gen_uuid)
    subscriber_id: Mapped[UUID] = mapped_column(ForeignKey("subscribers.id"))
    edital_id: Mapped[UUID] = mapped_column(ForeignKey("editais.id"))
    score: Mapped[float] = mapped_column(Float)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    explanation_json: Mapped[dict] = mapped_column(JSON, default=dict)
