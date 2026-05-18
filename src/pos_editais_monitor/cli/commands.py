"""Implementacoes async dos comandos da CLI."""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from pos_editais_monitor.core.config import get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.core.observability import setup_prometheus_endpoint
from pos_editais_monitor.domain.entities.fonte import Fonte
from pos_editais_monitor.domain.entities.subscriber import (
    AreaAlvo,
    MatchMode,
    SubscriberProfile,
)
from pos_editais_monitor.domain.enums.fonte_tipo import FonteTipo
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.infrastructure.cache.redis_client import get_redis
from pos_editais_monitor.infrastructure.db.repositories import (
    FonteRepository,
    SubscriberRepository,
)
from pos_editais_monitor.infrastructure.db.session import get_session
from pos_editais_monitor.infrastructure.emec.whitelist import EmecWhitelist
from pos_editais_monitor.infrastructure.llm.anthropic_client import AnthropicLLMClient
from pos_editais_monitor.pipeline.dead_letter import DeadLetterQueue
from pos_editais_monitor.pipeline.orchestrator import PipelineOrchestrator
from pos_editais_monitor.scheduling.jobs import refresh_emec_job
from pos_editais_monitor.scheduling.scheduler import build_scheduler
from pos_editais_monitor.scraping.clients.http_client import HttpClient
from pos_editais_monitor.scraping.clients.playwright_client import PlaywrightClient
from pos_editais_monitor.scraping.spiders import SPIDER_REGISTRY

log = get_logger(__name__)


async def run_single_spider(name: str) -> None:
    settings = get_settings()
    cls = SPIDER_REGISTRY.get(name)
    if not cls:
        log.error("unknown_spider", name=name, available=list(SPIDER_REGISTRY))
        raise SystemExit(2)

    redis = get_redis()
    dlq = DeadLetterQueue(redis)
    http = HttpClient(settings=settings, redis=redis)
    playwright = PlaywrightClient(settings=settings)

    # Whitelist seed in-memory: usa DB se houver, senao vazia
    from pos_editais_monitor.infrastructure.db.repositories import IESRepository
    async with get_session() as session:
        ies_list = await IESRepository(session).list_elegiveis()
    whitelist = EmecWhitelist(ies_list)

    llm = AnthropicLLMClient(settings) if settings.llm_enabled else None
    orchestrator = PipelineOrchestrator(
        whitelist=whitelist, dlq=dlq, settings=settings, llm=llm
    )
    spider = cls(http=http, playwright=playwright)
    try:
        stats = await orchestrator.run_spider(spider)
        log.info("scrape_cli_done", **asdict(stats))
    finally:
        await http.aclose()
        await playwright.aclose()


async def run_worker() -> None:
    settings = get_settings()
    if settings.prometheus_enabled:
        setup_prometheus_endpoint(settings.prometheus_port)
        log.info("prometheus_endpoint_up", port=settings.prometheus_port)

    # Boot: garante whitelist em DB
    await refresh_emec_job()

    sched = build_scheduler()
    sched.start()
    log.info("worker_started")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        log.info("worker_stopping")
    finally:
        sched.shutdown()


async def seed_initial_data() -> None:
    """Insere o subscriber padrao 'fabricio' e fontes do MVP."""
    async with get_session() as session:
        sub_repo = SubscriberRepository(session)
        fonte_repo = FonteRepository(session)

        profile = SubscriberProfile(
            nome="fabricio",
            email="fabricioguidine@gmail.com",
            formacao="bacharelado_ciencia_computacao",
            areas_alvo=[
                AreaAlvo(codigo_cnpq="10300007", modo=MatchMode.EXACT, peso=1.0),
                AreaAlvo(
                    codigo_cnpq="10700001",
                    modo=MatchMode.CROSS_DISCIPLINE,
                    peso=0.7,
                    requer_aceita_cs=True,
                ),
            ],
            # SO especializacao e MBA — sem mestrado/doutorado por escolha do user
            niveis_aceitos={Nivel.ESPECIALIZACAO, Nivel.MBA},
            score_minimo=0.70,
        )
        await sub_repo.upsert(profile)

        for codigo, nome, tipo, base in [
            ("dou", "Diario Oficial da Uniao", FonteTipo.DOU, "https://www.in.gov.br"),
            ("sucupira", "Plataforma Sucupira (CAPES)", FonteTipo.CAPES, "https://sucupira.capes.gov.br"),
            ("emec", "Cadastro e-MEC", FonteTipo.EMEC, "https://emec.mec.gov.br"),
        ]:
            await fonte_repo.upsert(
                Fonte(
                    codigo=codigo,
                    nome=nome,
                    tipo=tipo,
                    base_url=base,
                    spider_class=f"pos_editais_monitor.scraping.spiders.{codigo}",
                )
            )
    log.info("seed_completed")
