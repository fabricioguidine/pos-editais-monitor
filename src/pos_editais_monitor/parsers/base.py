"""Interface Parser + ParseResult.

Decisao: Parser eh um Protocol, nao classe abstrata, para permitir composicao
com funcoes simples. ParseResult eh imutavel (dataclass frozen).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.scraping.types import RawResponse


@dataclass(frozen=True, slots=True)
class ParseResult:
    edital: ParsedEdital
    confidence: float


class Parser(Protocol):
    """Interface dos parsers."""

    name: str

    def can_handle(self, raw: RawResponse) -> bool:
        """Retorna True se este parser sabe lidar com `raw`."""

    async def parse(self, raw: RawResponse) -> ParseResult:
        """Extrai. Pode levantar `ParserError`."""
