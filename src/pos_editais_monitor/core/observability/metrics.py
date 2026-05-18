"""Metricas Prometheus centralizadas.

Todas as metricas vivem aqui para evitar registros duplicados e facilitar grep.
"""

from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import Counter, Histogram, start_http_server


@dataclass(frozen=True, slots=True)
class _MetricsRegistry:
    spider_requests_total: Counter
    spider_request_latency_seconds: Histogram
    spider_contract_violations_total: Counter
    parser_failures_total: Counter
    pipeline_items_processed_total: Counter
    dedup_hits_total: Counter
    llm_fallback_invocations_total: Counter
    llm_tokens_total: Counter
    matches_total: Counter
    notifications_sent_total: Counter


METRICS = _MetricsRegistry(
    spider_requests_total=Counter(
        "pem_spider_requests_total",
        "Total HTTP requests issued by spiders",
        labelnames=("spider", "status"),
    ),
    spider_request_latency_seconds=Histogram(
        "pem_spider_request_latency_seconds",
        "Latency of spider HTTP requests in seconds",
        labelnames=("spider",),
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    ),
    spider_contract_violations_total=Counter(
        "pem_spider_contract_violations_total",
        "Times a spider response violated its contract assertions",
        labelnames=("spider", "reason"),
    ),
    parser_failures_total=Counter(
        "pem_parser_failures_total",
        "Parser failures by parser and reason",
        labelnames=("parser", "reason"),
    ),
    pipeline_items_processed_total=Counter(
        "pem_pipeline_items_processed_total",
        "Items processed by each pipeline stage",
        labelnames=("stage", "outcome"),
    ),
    dedup_hits_total=Counter(
        "pem_dedup_hits_total",
        "Dedup hits by kind",
        labelnames=("kind",),  # exact | simhash_near | update
    ),
    llm_fallback_invocations_total=Counter(
        "pem_llm_fallback_invocations_total",
        "LLM fallback invocations by reason",
        labelnames=("reason",),
    ),
    llm_tokens_total=Counter(
        "pem_llm_tokens_total",
        "LLM token usage (input/output, cached/uncached)",
        labelnames=("kind",),
    ),
    matches_total=Counter(
        "pem_matches_total",
        "Match records produced",
        labelnames=("profile", "score_bucket"),
    ),
    notifications_sent_total=Counter(
        "pem_notifications_sent_total",
        "Notifications sent",
        labelnames=("channel", "outcome"),
    ),
)


def setup_prometheus_endpoint(port: int) -> None:
    """Sobe um HTTP server para /metrics. Chamado pelo worker, nao pela API."""
    start_http_server(port)
