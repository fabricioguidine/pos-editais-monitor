from __future__ import annotations

from enum import StrEnum


class StatusEdital(StrEnum):
    """Ciclo de vida do edital."""

    DESCOBERTO = "descoberto"      # spider encontrou, ainda nao processado
    NORMALIZADO = "normalizado"    # parsed e validado
    CLASSIFICADO = "classificado"  # area CNPq atribuida
    PUBLICADO = "publicado"        # disponivel via API e elegivel para matching
    EXPIRADO = "expirado"          # prazo de inscricao passou
    INVALIDADO = "invalidado"      # detectado como nao-pertinente (privado pago, etc.)
