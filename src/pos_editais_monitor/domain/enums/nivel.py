from __future__ import annotations

import re
from enum import StrEnum

_DOUTORADO_RE = re.compile(r"\bdoutorad[oa]s?\b|\bphd\b", re.IGNORECASE)
_MBA_RE = re.compile(r"\bmba\b", re.IGNORECASE)
_MEST_PROF_RE = re.compile(r"\bmestrado\s+profissional\b", re.IGNORECASE)
_MESTRADO_RE = re.compile(r"\bmestrado\b|\bmestre\b", re.IGNORECASE)
_ESPECIALIZACAO_RE = re.compile(r"\bespecializa[cç][ãa]o\b|\blato\s+sensu\b", re.IGNORECASE)


class Nivel(StrEnum):
    """Nivel da pos-graduacao oferecida pelo edital."""

    ESPECIALIZACAO = "especializacao"
    MBA = "mba"
    MESTRADO_ACADEMICO = "mestrado_academico"
    MESTRADO_PROFISSIONAL = "mestrado_profissional"
    DOUTORADO = "doutorado"
    DESCONHECIDO = "desconhecido"

    @classmethod
    def from_text(cls, text: str, *, title: str | None = None) -> Nivel:
        """Mapeia texto livre para nivel. Prioriza o titulo quando fornecido.

        Trabalha em duas passadas:
        1. Tenta inferir a partir do titulo (mais especifico)
        2. Se vier DESCONHECIDO do titulo, tenta no texto completo
        """
        if title:
            r = cls._scan(title)
            if r is not cls.DESCONHECIDO:
                return r
        return cls._scan(text or "")

    @classmethod
    def _scan(cls, t: str) -> Nivel:
        if _MBA_RE.search(t):
            return cls.MBA
        if _MEST_PROF_RE.search(t):
            return cls.MESTRADO_PROFISSIONAL
        # Mestrado e Doutorado coexistem em muitos editais; preferimos
        # MESTRADO se aparecer (titulo costuma especificar)
        has_mestrado = bool(_MESTRADO_RE.search(t))
        has_doutorado = bool(_DOUTORADO_RE.search(t))
        if has_mestrado and not has_doutorado:
            return cls.MESTRADO_ACADEMICO
        if has_doutorado and not has_mestrado:
            return cls.DOUTORADO
        if has_mestrado and has_doutorado:
            return cls.MESTRADO_ACADEMICO   # tie-break: mestrado mais inclusivo
        if _ESPECIALIZACAO_RE.search(t):
            return cls.ESPECIALIZACAO
        return cls.DESCONHECIDO
