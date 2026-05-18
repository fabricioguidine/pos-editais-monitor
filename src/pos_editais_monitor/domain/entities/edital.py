"""Entidades de dominio para edital.

Convencao:
- `ParsedEdital`: DTO mutavel produzido pelos parsers. Carrega confidence.
- `Edital`: entidade canonica, persistida. Imutavel (slots + frozen=False
  apenas para permitir Pydantic, mas tratada como imutavel).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pos_editais_monitor.core.utils import utcnow
from typing import Any
from uuid import UUID, uuid4

from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.domain.enums.status_edital import StatusEdital
from pos_editais_monitor.domain.value_objects.identificador import IdentificadorExterno
from pos_editais_monitor.domain.value_objects.periodo import PeriodoInscricao


@dataclass(slots=True)
class ParsedEdital:
    """Resultado de um parser. Mutavel e carrega informacao de confianca."""

    titulo: str
    ies_nome: str
    fonte_codigo: str
    nivel: Nivel = Nivel.DESCONHECIDO
    modalidade: Modalidade = Modalidade.DESCONHECIDA
    area_concentracao: str | None = None
    area_cnpq_codigo: str | None = None
    is_gratuito: bool | None = None
    vagas: int | None = None
    periodo_inscricao: PeriodoInscricao | None = None
    identificador_externo: IdentificadorExterno | None = None
    url_origem: str = ""
    url_pdf: str | None = None
    texto_resumo: str | None = None
    texto_completo: str = ""
    confidence: float = 0.0
    parser_name: str = "unknown"
    extras: dict[str, Any] = field(default_factory=dict)

    def is_high_confidence(self, threshold: float) -> bool:
        return self.confidence >= threshold


@dataclass(slots=True)
class Edital:
    """Entidade canonica de edital, com ciclo de vida."""

    id: UUID = field(default_factory=uuid4)
    titulo: str = ""
    ies_id: UUID | None = None
    fonte_id: UUID | None = None
    nivel: Nivel = Nivel.DESCONHECIDO
    modalidade: Modalidade = Modalidade.DESCONHECIDA
    area_cnpq_codigo: str | None = None
    is_gratuito: bool = False
    vagas: int | None = None
    periodo_inscricao: PeriodoInscricao | None = None
    identificador_externo: IdentificadorExterno | None = None
    url_origem: str = ""
    url_pdf: str | None = None
    texto_resumo: str | None = None
    canonical_hash: str = ""
    simhash: int = 0
    status: StatusEdital = StatusEdital.DESCOBERTO
    criado_em: datetime = field(default_factory=utcnow)
    atualizado_em: datetime = field(default_factory=utcnow)

    def marcar_expirado_se_aplicavel(self) -> None:
        if self.periodo_inscricao and self.periodo_inscricao.expirado:
            self.status = StatusEdital.EXPIRADO
            self.atualizado_em = utcnow()
