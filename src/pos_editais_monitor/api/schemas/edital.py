from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from pos_editais_monitor.domain.entities.edital import Edital


class EditalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    titulo: str
    nivel: str
    modalidade: str
    area_cnpq_codigo: str | None
    is_gratuito: bool
    vagas: int | None
    inscricao_de: date | None
    inscricao_ate: date | None
    url_origem: str
    url_pdf: str | None
    texto_resumo: str | None
    status: str
    canonical_hash: str
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def from_entity(cls, e: Edital) -> "EditalRead":
        return cls(
            id=e.id,
            titulo=e.titulo,
            nivel=e.nivel.value,
            modalidade=e.modalidade.value,
            area_cnpq_codigo=e.area_cnpq_codigo,
            is_gratuito=e.is_gratuito,
            vagas=e.vagas,
            inscricao_de=e.periodo_inscricao.de if e.periodo_inscricao else None,
            inscricao_ate=e.periodo_inscricao.ate if e.periodo_inscricao else None,
            url_origem=e.url_origem,
            url_pdf=e.url_pdf,
            texto_resumo=e.texto_resumo,
            status=e.status.value,
            canonical_hash=e.canonical_hash,
            criado_em=e.criado_em,
            atualizado_em=e.atualizado_em,
        )
