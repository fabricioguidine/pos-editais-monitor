"""OpenTelemetry tracing setup. Idempotente."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_initialized = False


def setup_tracing(service_name: str, otlp_endpoint: str, enabled: bool = True) -> None:
    """Configura tracing global. No-op se enabled=False ou se ja inicializado."""
    global _initialized
    if not enabled or _initialized:
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True
