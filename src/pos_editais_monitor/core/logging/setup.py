"""Configuracao de logging com structlog.

- dev: console colorido, KV pairs
- prod: JSON estruturado, pronto para shipping (Loki/CloudWatch)
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def _add_app_context(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Adiciona campos comuns a todos os logs."""
    event_dict.setdefault("app", "pos-editais-monitor")
    return event_dict


def configure_logging(level: str = "INFO", fmt: str = "console") -> None:
    """Configura structlog + stdlib logging.

    Deve ser chamado uma unica vez na inicializacao do processo.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # stdlib logging baseline
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _add_app_context,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if fmt == "json":
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.plain_traceback)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
