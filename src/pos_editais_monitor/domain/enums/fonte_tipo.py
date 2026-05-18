from __future__ import annotations

from enum import StrEnum


class FonteTipo(StrEnum):
    """Categorias de fonte para roteamento de parser e estrategia de scraping."""

    CAPES = "capes"
    UAB = "uab"
    UNIVERSIDADE_FEDERAL = "universidade_federal"
    INSTITUTO_FEDERAL = "instituto_federal"
    UNIVERSIDADE_ESTADUAL = "universidade_estadual"
    SIGAA = "sigaa"
    DOU = "dou"
    EMEC = "emec"
    OUTRO = "outro"
