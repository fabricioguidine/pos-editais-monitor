"""FastAPI app factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from pos_editais_monitor import __version__
from pos_editais_monitor.api.routers import editais, health
from pos_editais_monitor.core.config import get_settings
from pos_editais_monitor.core.logging import configure_logging, get_logger
from pos_editais_monitor.core.observability import setup_tracing

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    setup_tracing(
        service_name="pos-editais-monitor-api",
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        enabled=settings.otel_enabled,
    )
    log.info("api_starting", env=settings.env, version=__version__)
    yield
    log.info("api_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="pos-editais-monitor",
        version=__version__,
        description="Monitor de editais de pos-graduacao gratuitos no Brasil",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(editais.router)
    if settings.otel_enabled:
        FastAPIInstrumentor.instrument_app(app)
    return app


app = create_app()
