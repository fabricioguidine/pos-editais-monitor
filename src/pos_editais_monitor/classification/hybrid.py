"""Classificador hibrido: tenta rules; se confidence baixa, usa LLM enricher.

Decisao: classificacao por area NAO eh prioridade-1 pro LLM fallback hoje.
Mais barato classificar por keyword. Se vazio, retornamos None (matcher
descarta por hard filter de area).
"""

from __future__ import annotations

from pos_editais_monitor.classification.rules_classifier import (
    ClassificationResult,
    RulesClassifier,
)
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import ParsedEdital

log = get_logger(__name__)


class HybridClassifier:
    def __init__(self, threshold: float = 0.5) -> None:
        self._rules = RulesClassifier()
        self._threshold = threshold

    def classify(self, p: ParsedEdital) -> ClassificationResult:
        result = self._rules.classify(p)
        if result.confidence < self._threshold:
            log.debug(
                "classification_low_confidence",
                title=p.titulo[:80],
                area=result.area_cnpq_codigo,
                conf=result.confidence,
            )
        return result
