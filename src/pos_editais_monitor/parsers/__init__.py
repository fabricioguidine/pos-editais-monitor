"""Parsers: extraem campos estruturados de respostas brutas."""

from pos_editais_monitor.parsers.base import Parser, ParseResult
from pos_editais_monitor.parsers.registry import ParserRegistry, get_default_registry

__all__ = ["Parser", "ParseResult", "ParserRegistry", "get_default_registry"]
