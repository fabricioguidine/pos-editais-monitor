"""Registry de parsers — strategy pattern + chain of responsibility.

Cada parser e adicionado em ordem. resolve() retorna o primeiro com
can_handle == True. Spider-specific parsers ficam antes dos genericos.
"""

from __future__ import annotations

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.parsers.base import Parser
from pos_editais_monitor.scraping.types import RawResponse

log = get_logger(__name__)


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[Parser] = []

    def register(self, parser: Parser) -> None:
        log.debug("parser_registered", name=parser.name)
        self._parsers.append(parser)

    def resolve(self, raw: RawResponse) -> Parser | None:
        for p in self._parsers:
            if p.can_handle(raw):
                return p
        return None

    @property
    def size(self) -> int:
        return len(self._parsers)


_default: ParserRegistry | None = None


def get_default_registry() -> ParserRegistry:
    """Lazy import dos parsers concretos para evitar ciclo."""
    global _default
    if _default is not None:
        return _default
    reg = ParserRegistry()

    from pos_editais_monitor.parsers.html.generic import GenericHtmlParser
    from pos_editais_monitor.parsers.pdf.pdf_parser import PdfParser
    from pos_editais_monitor.parsers.wordpress.wp_parser import WordPressParser

    # Ordem importa: especificos primeiro
    reg.register(WordPressParser())
    reg.register(PdfParser())
    reg.register(GenericHtmlParser())
    _default = reg
    return reg
