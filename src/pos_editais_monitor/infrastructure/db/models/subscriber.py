from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from pos_editais_monitor.infrastructure.db.base import Base, TimestampMixin, gen_uuid


class SubscriberModel(TimestampMixin, Base):
    __tablename__ = "subscribers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=gen_uuid)
    nome: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    formacao: Mapped[str] = mapped_column(String(128), default="")
    profile_json: Mapped[dict] = mapped_column(JSON)   # serialized SubscriberProfile
    score_minimo: Mapped[float] = mapped_column(Float, default=0.70)
    digest_cron: Mapped[str] = mapped_column(String(64), default="0 7 * * *")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
