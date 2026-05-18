from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from pos_editais_monitor.domain.entities.fonte import Fonte
from pos_editais_monitor.domain.enums.fonte_tipo import FonteTipo
from pos_editais_monitor.infrastructure.db.base import Base, TimestampMixin, gen_uuid


class FonteModel(TimestampMixin, Base):
    __tablename__ = "fontes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=gen_uuid)
    codigo: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(64), default=FonteTipo.OUTRO.value)
    base_url: Mapped[str] = mapped_column(String(512), default="")
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    intervalo_minutos: Mapped[int] = mapped_column(Integer, default=180)
    spider_class: Mapped[str] = mapped_column(String(255), default="")
    ultima_execucao: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultima_execucao_status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def to_entity(self) -> Fonte:
        return Fonte(
            id=self.id,
            codigo=self.codigo,
            nome=self.nome,
            tipo=FonteTipo(self.tipo),
            base_url=self.base_url,
            ativa=self.ativa,
            intervalo_minutos=self.intervalo_minutos,
            spider_class=self.spider_class,
            ultima_execucao=self.ultima_execucao,
            ultima_execucao_status=self.ultima_execucao_status,
        )

    @classmethod
    def from_entity(cls, f: Fonte) -> "FonteModel":
        return cls(
            id=f.id,
            codigo=f.codigo,
            nome=f.nome,
            tipo=f.tipo.value,
            base_url=f.base_url,
            ativa=f.ativa,
            intervalo_minutos=f.intervalo_minutos,
            spider_class=f.spider_class,
            ultima_execucao=f.ultima_execucao,
            ultima_execucao_status=f.ultima_execucao_status,
        )
