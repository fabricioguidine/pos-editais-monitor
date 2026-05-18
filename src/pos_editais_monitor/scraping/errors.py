"""Erros tipados do scraping layer."""

from __future__ import annotations


class ScrapingError(Exception):
    """Base."""


class RobotsDisallowedError(ScrapingError):
    """URL bloqueada pelo robots.txt."""


class CircuitOpenError(ScrapingError):
    """Circuit breaker do host esta aberto."""


class RateLimitedError(ScrapingError):
    """Resposta 429 ou Retry-After do servidor."""


class ContractViolationError(ScrapingError):
    """Resposta do spider violou contrato (sem conteudo esperado)."""


class ParserError(ScrapingError):
    """Falha de parser."""
