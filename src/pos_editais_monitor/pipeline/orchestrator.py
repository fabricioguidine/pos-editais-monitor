"""Orchestrator do pipeline.

Fluxo por spider:
  discover_urls -> fetch -> parse -> (LLM enrich se baixo confidence)
  -> dedup -> classify -> persist -> match -> (envio postergado p/ digest)

Implementacao MVP: sequencial dentro de cada item (asyncio gather entre items
controlado por semaforo). Trocar por queues + workers se gargalo aparecer.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pos_editais_monitor.classification.hybrid import HybridClassifier
from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.core.observability import METRICS
from pos_editais_monitor.dedup.canonical_hash import canonical_hash
from pos_editais_monitor.dedup.change_detector import ChangeDetector, ChangeKind
from pos_editais_monitor.dedup.simhash import compute_simhash
from pos_editais_monitor.domain.entities.edital import Edital, ParsedEdital
from pos_editais_monitor.domain.enums.status_edital import StatusEdital
from pos_editais_monitor.infrastructure.db.session import get_session
from pos_editais_monitor.infrastructure.db.repositories import (
    EditalRepository,
    IESRepository,
    MatchRepository,
    SubscriberRepository,
)
from pos_editais_monitor.infrastructure.emec.whitelist import EmecWhitelist
from pos_editais_monitor.infrastructure.llm.anthropic_client import AnthropicLLMClient
from pos_editais_monitor.matching.engine import MatchEngine
from pos_editais_monitor.parsers.pdf.llm_fallback import LLMEditalEnricher
from pos_editais_monitor.pipeline.dead_letter import DeadLetterQueue
from pos_editais_monitor.scraping.errors import ScrapingError

if TYPE_CHECKING:
    from pos_editais_monitor.scraping.spiders.base.spider import BaseSpider

log = get_logger(__name__)


@dataclass(slots=True)
class PipelineStats:
    discovered: int = 0
    parsed: int = 0
    enriched_by_llm: int = 0
    persisted: int = 0
    matched: int = 0
    failed: int = 0


class PipelineOrchestrator:
    def __init__(
        self,
        *,
        whitelist: EmecWhitelist,
        dlq: DeadLetterQueue,
        settings: Settings | None = None,
        llm: AnthropicLLMClient | None = None,
        concurrency: int = 4,
    ) -> None:
        self._settings = settings or get_settings()
        self._whitelist = whitelist
        self._dlq = dlq
        self._classifier = HybridClassifier()
        self._matcher = MatchEngine(whitelist)
        self._change_detector = ChangeDetector()
        self._llm = llm
        self._llm_enricher = LLMEditalEnricher(llm) if llm else None
        self._sem = asyncio.Semaphore(concurrency)

    async def run_spider(self, spider: "BaseSpider") -> PipelineStats:
        stats = PipelineStats()
        log.info("spider_run_start", spider=spider.name)
        tasks: list[asyncio.Task[None]] = []
        async for url in spider.discover_urls():
            stats.discovered += 1
            tasks.append(asyncio.create_task(self._process_url(spider, url, stats)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=False)
        log.info(
            "spider_run_end",
            spider=spider.name,
            discovered=stats.discovered,
            parsed=stats.parsed,
            enriched=stats.enriched_by_llm,
            persisted=stats.persisted,
            matched=stats.matched,
            failed=stats.failed,
        )
        return stats

    async def _process_url(
        self, spider: "BaseSpider", url: str, stats: PipelineStats
    ) -> None:
        async with self._sem:
            try:
                raw = await spider.fetch(url)
            except ScrapingError as exc:
                log.warning("fetch_failed", url=url, spider=spider.name, err=str(exc))
                METRICS.pipeline_items_processed_total.labels("fetch", "error").inc()
                stats.failed += 1
                await self._dlq.push("fetch", str(exc), {"url": url, "spider": spider.name})
                return

            METRICS.pipeline_items_processed_total.labels("fetch", "ok").inc()
            try:
                async for parsed in spider.parse_response(raw):
                    stats.parsed += 1
                    await self._process_parsed(parsed, stats)
            except Exception as exc:  # noqa: BLE001
                log.error("parse_pipeline_error", url=url, err=str(exc), exc_info=True)
                METRICS.pipeline_items_processed_total.labels("parse", "error").inc()
                stats.failed += 1
                await self._dlq.push("parse", str(exc), {"url": url})

    async def _process_parsed(self, parsed: ParsedEdital, stats: PipelineStats) -> None:
        # Stage: LLM enrich se baixa confidence
        if (
            self._llm_enricher
            and parsed.confidence < self._settings.llm_confidence_threshold
        ):
            result = await self._llm_enricher.enrich(parsed)
            parsed = result.edital
            stats.enriched_by_llm += 1

        # Stage: dedup hashes
        c_hash = canonical_hash(parsed)
        s_hash = compute_simhash(parsed.texto_resumo or parsed.titulo)

        # Stage: classify
        cls = self._classifier.classify(parsed)
        if cls.area_cnpq_codigo:
            parsed.area_cnpq_codigo = cls.area_cnpq_codigo

        async with get_session() as session:
            ies_repo = IESRepository(session)
            ed_repo = EditalRepository(session)
            match_repo = MatchRepository(session)
            sub_repo = SubscriberRepository(session)

            ies = await ies_repo.find_by_sigla_or_nome(parsed.ies_nome) if parsed.ies_nome else None

            # Stage: persist
            existing = await ed_repo.get_by_canonical_hash(c_hash)
            change = self._change_detector.classify(existing, s_hash)

            ent = Edital(
                titulo=parsed.titulo,
                ies_id=ies.id if ies else None,
                fonte_id=None,
                nivel=parsed.nivel,
                modalidade=parsed.modalidade,
                area_cnpq_codigo=parsed.area_cnpq_codigo,
                is_gratuito=bool(parsed.is_gratuito) if parsed.is_gratuito is not None else True,
                vagas=parsed.vagas,
                periodo_inscricao=parsed.periodo_inscricao,
                identificador_externo=parsed.identificador_externo,
                url_origem=parsed.url_origem,
                url_pdf=parsed.url_pdf,
                texto_resumo=parsed.texto_resumo,
                canonical_hash=c_hash,
                simhash=s_hash,
                status=StatusEdital.PUBLICADO,
            )
            persisted = await ed_repo.upsert(ent)
            stats.persisted += 1
            METRICS.dedup_hits_total.labels(change.value).inc()

            if change is ChangeKind.COSMETIC:
                METRICS.pipeline_items_processed_total.labels("persist", "cosmetic").inc()
                return    # nao matcheia/notifica em update cosmetico

            METRICS.pipeline_items_processed_total.labels("persist", "ok").inc()

            # Stage: match para cada subscriber ativo
            for profile in await sub_repo.list_ativos():
                result = self._matcher.evaluate(persisted, parsed.ies_nome, profile)
                if not result.matched:
                    continue
                bucket = "high" if result.score >= 0.85 else "mid"
                METRICS.matches_total.labels(profile.nome, bucket).inc()
                await match_repo.add(
                    subscriber_id=profile.id,
                    edital_id=persisted.id,
                    score=result.score,
                    explanation=result.as_explanation(),
                )
                stats.matched += 1
                log.info(
                    "match_recorded",
                    profile=profile.nome,
                    score=result.score,
                    edital=persisted.titulo[:80],
                )
