from __future__ import annotations

import re
from enum import StrEnum

_UAB_RE = re.compile(r"\bUAB\b|universidade\s+aberta", re.IGNORECASE)
_SEMI_RE = re.compile(r"\bsemipresencial\b|\bsemi-presencial\b|h[ií]brid[oa]", re.IGNORECASE)
_EAD_RE = re.compile(
    r"\bEAD\b|\bensino\s+a\s+dist[aâ]ncia\b|\ba\s+dist[aâ]ncia\b|\bonline\b",
    re.IGNORECASE,
)
_PRESENCIAL_RE = re.compile(r"\bpresencial\b", re.IGNORECASE)


class Modalidade(StrEnum):
    """Modalidade de oferta do programa."""

    PRESENCIAL = "presencial"
    EAD = "ead"
    SEMIPRESENCIAL = "semipresencial"
    UAB = "uab"
    DESCONHECIDA = "desconhecida"

    @classmethod
    def from_text(cls, text: str) -> Modalidade:
        t = text or ""
        if _UAB_RE.search(t):
            return cls.UAB
        if _SEMI_RE.search(t):
            return cls.SEMIPRESENCIAL
        if _EAD_RE.search(t):
            return cls.EAD
        if _PRESENCIAL_RE.search(t):
            return cls.PRESENCIAL
        return cls.DESCONHECIDA
