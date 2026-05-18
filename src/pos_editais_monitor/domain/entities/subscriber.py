"""Subscriber profile - usado pelo matching engine para filtrar editais relevantes.

O MVP carrega o perfil 'fabricio' via fixture/seed:
  - bacharelado em Ciencia da Computacao
  - alvos: CC (exact) + Geociencias (cross_discipline)
  - precision-first (score_minimo alto)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel


class MatchMode(StrEnum):
    """Como uma area-alvo contribui ao score de matching."""

    EXACT = "exact"                          # match exato de codigo CNPq
    CROSS_DISCIPLINE = "cross_discipline"    # area aceita formacao do subscriber


@dataclass(slots=True)
class AreaAlvo:
    """Uma area do conhecimento alvo no perfil do subscriber."""

    codigo_cnpq: str
    modo: MatchMode = MatchMode.EXACT
    peso: float = 1.0
    requer_aceita_cs: bool = False   # para cross_discipline


@dataclass(slots=True)
class SubscriberProfile:
    """Perfil do assinante para personalizar matching."""

    id: UUID = field(default_factory=uuid4)
    nome: str = ""
    email: str = ""
    formacao: str = ""                  # ex.: "bacharelado_ciencia_computacao"
    areas_alvo: list[AreaAlvo] = field(default_factory=list)
    niveis_aceitos: set[Nivel] = field(
        default_factory=lambda: {
            Nivel.ESPECIALIZACAO,
            Nivel.MBA,
            Nivel.MESTRADO_ACADEMICO,
            Nivel.MESTRADO_PROFISSIONAL,
            Nivel.DOUTORADO,
        }
    )
    modalidades_aceitas: set[Modalidade] = field(
        default_factory=lambda: {
            Modalidade.PRESENCIAL,
            Modalidade.EAD,
            Modalidade.SEMIPRESENCIAL,
            Modalidade.UAB,
        }
    )
    apenas_gratuitos: bool = True
    apenas_ies_emec_publicas: bool = True
    score_minimo: float = 0.70
    digest_cron: str = "0 7 * * *"      # diario 07:00
    ativo: bool = True
