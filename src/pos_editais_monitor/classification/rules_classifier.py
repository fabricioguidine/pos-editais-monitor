"""Classificador rules-based: dicionario de palavras-chave -> area CNPq.

Para o MVP, focamos nas grandes areas relevantes para o subscriber padrao:
- Ciencia da Computacao (10300007)
- Geociencias (10700001)
- Matematica/Estatistica (10100002 / 10200006)
- Engenharias Eletrica/Producao (30400000 / 30900008)

Confidence: max(1.0, 0.3 + 0.1 * matches).
"""

from __future__ import annotations

from dataclasses import dataclass

from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.parsers.fields.normalize import normalize_to_ascii


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    area_cnpq_codigo: str | None
    confidence: float
    evidence: tuple[str, ...]


_KEYWORDS: dict[str, list[str]] = {
    "10300007": [
        "ciencia da computacao", "ciencias da computacao", "computacao",
        "inteligencia artificial", "machine learning", "engenharia de software",
        "ciencia de dados", "data science", "redes neurais", "sistemas distribuidos",
        "algoritmos", "banco de dados", "informatica",
    ],
    "10700001": [
        "geociencias", "ciencias da terra", "geologia", "geografia fisica",
        "geofisica", "geoquimica", "paleontologia", "sensoriamento remoto",
        "geoinformatica", "hidrogeologia", "geotecnia",
    ],
    "10100002": ["matematica", "matematica aplicada", "matematica pura"],
    "10200006": ["estatistica", "probabilidade", "bioestatistica"],
    "30400000": ["engenharia eletrica", "sistemas embarcados", "sinais"],
    "30900008": ["engenharia de producao", "pesquisa operacional"],
}


class RulesClassifier:
    name = "rules"

    def classify(self, p: ParsedEdital) -> ClassificationResult:
        haystack = " ".join(
            (
                p.titulo,
                p.texto_resumo or "",
                p.area_concentracao or "",
                p.texto_completo[:3000] if p.texto_completo else "",
            )
        )
        norm = normalize_to_ascii(haystack)
        best_code: str | None = None
        best_count = 0
        best_hits: list[str] = []
        for code, kws in _KEYWORDS.items():
            count = 0
            hits: list[str] = []
            for kw in kws:
                if kw in norm:
                    count += 1
                    hits.append(kw)
            if count > best_count:
                best_count = count
                best_code = code
                best_hits = hits
        if best_count == 0:
            return ClassificationResult(area_cnpq_codigo=None, confidence=0.0, evidence=())
        confidence = min(0.95, 0.3 + 0.15 * best_count)
        return ClassificationResult(
            area_cnpq_codigo=best_code,
            confidence=confidence,
            evidence=tuple(best_hits),
        )
