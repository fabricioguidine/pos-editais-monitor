from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, BigInteger, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from pos_editais_monitor.infrastructure.db.base import Base, TimestampMixin, gen_uuid


class SnapshotModel(TimestampMixin, Base):
    __tablename__ = "snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=gen_uuid)
    edital_id: Mapped[UUID | None] = mapped_column(ForeignKey("editais.id"), nullable=True)
    fonte_id: Mapped[UUID | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)
    url: Mapped[str] = mapped_column(String(1024))
    http_status: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str] = mapped_column(String(128), default="")
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    bytes_size: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_path: Mapped[str] = mapped_column(String(512))
    parser_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parse_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    headers: Mapped[dict] = mapped_column(JSON, default=dict)
