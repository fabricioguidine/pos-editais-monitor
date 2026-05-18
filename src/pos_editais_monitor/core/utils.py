"""Pequenos helpers compartilhados."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """datetime.now(UTC) - substitui datetime.utcnow() deprecado em 3.13.

    Retorna timezone-aware. Compativel com colunas SQLAlchemy DateTime(timezone=True).
    """
    return datetime.now(timezone.utc)
