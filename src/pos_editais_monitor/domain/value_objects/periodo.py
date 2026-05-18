from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class PeriodoInscricao:
    """Periodo de inscricao do edital. Imutavel."""

    de: date | None
    ate: date | None

    def __post_init__(self) -> None:
        if self.de and self.ate and self.de > self.ate:
            raise ValueError(f"Periodo invalido: de={self.de} > ate={self.ate}")

    @property
    def aberto(self) -> bool:
        hoje = date.today()
        if self.de and hoje < self.de:
            return False
        if self.ate and hoje > self.ate:
            return False
        return True

    @property
    def expirado(self) -> bool:
        return self.ate is not None and self.ate < date.today()

    def isoformat(self) -> str:
        de = self.de.isoformat() if self.de else "?"
        ate = self.ate.isoformat() if self.ate else "?"
        return f"{de}..{ate}"
