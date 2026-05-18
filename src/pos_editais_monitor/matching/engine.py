"""Matching engine — precision-first.

Hard filters (eliminatorios):
- e_gratuito True
- IES esta na whitelist e-MEC
- nivel em profile.niveis_aceitos
- modalidade em profile.modalidades_aceitas

Soft scoring (cumulativo):
- match exato de area CNPq -> + alvo.peso
- match cross_discipline valido -> + alvo.peso
- threshold final >= profile.score_minimo
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import Edital
from pos_editais_monitor.domain.entities.subscriber import (
    AreaAlvo,
    MatchMode,
    SubscriberProfile,
)
from pos_editais_monitor.domain.enums.area_cnpq import ACEITAM_BACHAREIS_CC
from pos_editais_monitor.infrastructure.emec.whitelist import EmecWhitelist

log = get_logger(__name__)


@dataclass(slots=True)
class MatchResult:
    matched: bool
    score: float
    reasons: list[str] = field(default_factory=list)
    contributing_areas: list[str] = field(default_factory=list)

    def as_explanation(self) -> dict:
        return {
            "matched": self.matched,
            "score": self.score,
            "reasons": self.reasons,
            "contributing_areas": self.contributing_areas,
        }


class MatchEngine:
    def __init__(self, whitelist: EmecWhitelist) -> None:
        self._whitelist = whitelist

    def evaluate(
        self,
        edital: Edital,
        ies_nome: str,
        profile: SubscriberProfile,
    ) -> MatchResult:
        reasons: list[str] = []

        # Hard filters
        if profile.apenas_gratuitos and not edital.is_gratuito:
            reasons.append("hard:nao_gratuito")
            return MatchResult(matched=False, score=0.0, reasons=reasons)

        if profile.apenas_ies_emec_publicas and not self._whitelist.contains(ies_nome):
            reasons.append(f"hard:ies_fora_whitelist:{ies_nome[:60]}")
            return MatchResult(matched=False, score=0.0, reasons=reasons)

        if edital.nivel not in profile.niveis_aceitos:
            reasons.append(f"hard:nivel_nao_aceito:{edital.nivel.value}")
            return MatchResult(matched=False, score=0.0, reasons=reasons)

        if edital.modalidade not in profile.modalidades_aceitas:
            reasons.append(f"hard:modalidade_nao_aceita:{edital.modalidade.value}")
            return MatchResult(matched=False, score=0.0, reasons=reasons)

        # Soft scoring
        score = 0.0
        contributing: list[str] = []
        for alvo in profile.areas_alvo:
            contrib = self._score_alvo(alvo, edital)
            if contrib > 0.0:
                score += contrib
                contributing.append(f"{alvo.codigo_cnpq}:{alvo.modo.value}:+{contrib:.2f}")

        matched = score >= profile.score_minimo
        if matched:
            reasons.append(f"soft:score={score:.2f}>=min={profile.score_minimo}")
        else:
            reasons.append(f"soft:score={score:.2f}<min={profile.score_minimo}")

        return MatchResult(
            matched=matched,
            score=round(score, 3),
            reasons=reasons,
            contributing_areas=contributing,
        )

    @staticmethod
    def _score_alvo(alvo: AreaAlvo, edital: Edital) -> float:
        if not edital.area_cnpq_codigo:
            return 0.0
        if alvo.modo is MatchMode.EXACT:
            return alvo.peso if edital.area_cnpq_codigo == alvo.codigo_cnpq else 0.0
        # cross_discipline
        if alvo.codigo_cnpq != edital.area_cnpq_codigo:
            return 0.0
        # Edital esta na area alvo, mas aceita bachareis CS?
        if alvo.requer_aceita_cs and edital.area_cnpq_codigo not in ACEITAM_BACHAREIS_CC:
            return 0.0
        return alvo.peso
