from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IdentificadorExterno:
    """Identificador externo do edital (numero/codigo dado pela IES).

    Ex.: 'EDITAL 03/2026', 'PPGCC-2026-1'. Quando ausente, gera-se sintetico
    a partir do hash canonico.
    """

    valor: str
    fonte: str   # ex: "ufrgs-ppg", "capes"

    def __str__(self) -> str:
        return f"{self.fonte}:{self.valor}"
