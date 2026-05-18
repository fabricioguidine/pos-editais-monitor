"""Base declarativa SQLAlchemy 2.0 com tipos comuns."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base para todos os modelos. Configura naming convention e tipos UUID/timestamp."""

    type_annotation_map = {
        UUID: PgUUID(as_uuid=True),
    }


class TimestampMixin:
    """Mixin que adiciona created_at/updated_at gerenciados pelo banco."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def gen_uuid() -> UUID:
    return uuid4()
