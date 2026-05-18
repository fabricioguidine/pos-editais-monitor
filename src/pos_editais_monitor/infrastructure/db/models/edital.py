from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pos_editais_monitor.domain.entities.edital import Edital
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.domain.enums.status_edital import StatusEdital
from pos_editais_monitor.domain.value_objects.identificador import IdentificadorExterno
from pos_editais_monitor.domain.value_objects.periodo import PeriodoInscricao
from pos_editais_monitor.infrastructure.db.base import Base, TimestampMixin, gen_uuid


class EditalModel(TimestampMixin, Base):
    __tablename__ = "editais"
    __table_args__ = (
        Index("ix_editais_canonical_hash", "canonical_hash"),
        Index("ix_editais_simhash", "simhash"),
        Index("ix_editais_fonte_status", "fonte_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=gen_uuid)
    titulo: Mapped[str] = mapped_column(String(512))
    ies_id: Mapped[UUID | None] = mapped_column(ForeignKey("ies.id"), nullable=True)
    fonte_id: Mapped[UUID | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)
    nivel: Mapped[str] = mapped_column(String(32), default=Nivel.DESCONHECIDO.value)
    modalidade: Mapped[str] = mapped_column(String(32), default=Modalidade.DESCONHECIDA.value)
    area_cnpq_codigo: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    is_gratuito: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    vagas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inscricao_de: Mapped[date | None] = mapped_column(Date, nullable=True)
    inscricao_ate: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    identificador_externo_valor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identificador_externo_fonte: Mapped[str | None] = mapped_column(String(64), nullable=True)
    url_origem: Mapped[str] = mapped_column(String(1024), default="")
    url_pdf: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    texto_resumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    simhash: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(
        String(32), default=StatusEdital.DESCOBERTO.value, index=True
    )

    def to_entity(self) -> Edital:
        periodo = None
        if self.inscricao_de or self.inscricao_ate:
            periodo = PeriodoInscricao(de=self.inscricao_de, ate=self.inscricao_ate)
        ident = None
        if self.identificador_externo_valor and self.identificador_externo_fonte:
            ident = IdentificadorExterno(
                valor=self.identificador_externo_valor,
                fonte=self.identificador_externo_fonte,
            )
        return Edital(
            id=self.id,
            titulo=self.titulo,
            ies_id=self.ies_id,
            fonte_id=self.fonte_id,
            nivel=Nivel(self.nivel),
            modalidade=Modalidade(self.modalidade),
            area_cnpq_codigo=self.area_cnpq_codigo,
            is_gratuito=self.is_gratuito,
            vagas=self.vagas,
            periodo_inscricao=periodo,
            identificador_externo=ident,
            url_origem=self.url_origem,
            url_pdf=self.url_pdf,
            texto_resumo=self.texto_resumo,
            canonical_hash=self.canonical_hash,
            simhash=_to_unsigned64(self.simhash),
            status=StatusEdital(self.status),
            criado_em=self.created_at,
            atualizado_em=self.updated_at,
        )

    @classmethod
    def from_entity(cls, e: Edital) -> "EditalModel":
        return cls(
            id=e.id,
            titulo=e.titulo,
            ies_id=e.ies_id,
            fonte_id=e.fonte_id,
            nivel=e.nivel.value,
            modalidade=e.modalidade.value,
            area_cnpq_codigo=e.area_cnpq_codigo,
            is_gratuito=e.is_gratuito,
            vagas=e.vagas,
            inscricao_de=e.periodo_inscricao.de if e.periodo_inscricao else None,
            inscricao_ate=e.periodo_inscricao.ate if e.periodo_inscricao else None,
            identificador_externo_valor=(
                e.identificador_externo.valor if e.identificador_externo else None
            ),
            identificador_externo_fonte=(
                e.identificador_externo.fonte if e.identificador_externo else None
            ),
            url_origem=e.url_origem,
            url_pdf=e.url_pdf,
            texto_resumo=e.texto_resumo,
            canonical_hash=e.canonical_hash,
            # Simhash eh uint64; Postgres BIGINT eh int64 signed. Converte.
            simhash=_to_signed64(e.simhash),
            status=e.status.value,
        )


def _to_signed64(v: int) -> int:
    """Converte unsigned 64-bit para signed 64-bit (BIGINT). Reversivel."""
    return v - (1 << 64) if v >= (1 << 63) else v


def _to_unsigned64(v: int) -> int:
    """Inverso de _to_signed64."""
    return v + (1 << 64) if v < 0 else v
