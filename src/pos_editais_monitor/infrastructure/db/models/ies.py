from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from pos_editais_monitor.domain.entities.ies import IES
from pos_editais_monitor.infrastructure.db.base import Base, TimestampMixin, gen_uuid


class IESModel(TimestampMixin, Base):
    __tablename__ = "ies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=gen_uuid)
    codigo_emec: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sigla: Mapped[str] = mapped_column(String(32), index=True)
    nome: Mapped[str] = mapped_column(String(255))
    categoria_administrativa: Mapped[str] = mapped_column(String(64), default="")
    organizacao_academica: Mapped[str] = mapped_column(String(64), default="")
    uf: Mapped[str] = mapped_column(String(4), default="")
    municipio: Mapped[str] = mapped_column(String(128), default="")
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    gratuita: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    def to_entity(self) -> IES:
        return IES(
            id=self.id,
            codigo_emec=self.codigo_emec,
            sigla=self.sigla,
            nome=self.nome,
            categoria_administrativa=self.categoria_administrativa,
            organizacao_academica=self.organizacao_academica,
            uf=self.uf,
            municipio=self.municipio,
            ativa=self.ativa,
            gratuita=self.gratuita,
            atualizado_em=self.updated_at,
        )

    @classmethod
    def from_entity(cls, i: IES) -> "IESModel":
        return cls(
            id=i.id,
            codigo_emec=i.codigo_emec,
            sigla=i.sigla,
            nome=i.nome,
            categoria_administrativa=i.categoria_administrativa,
            organizacao_academica=i.organizacao_academica,
            uf=i.uf,
            municipio=i.municipio,
            ativa=i.ativa,
            gratuita=i.gratuita,
        )
