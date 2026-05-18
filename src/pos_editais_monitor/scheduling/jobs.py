"""Jobs orquestrados pelo scheduler.

Em modulo separado para facilitar testar isoladamente (cada job e uma
funcao async que recebe dependencias por argumento ou via singleton).
"""

from __future__ import annotations

from datetime import date

from pos_editais_monitor.core.config import get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.enums.area_cnpq import get_by_codigo
from pos_editais_monitor.infrastructure.cache.redis_client import get_redis
from pos_editais_monitor.infrastructure.db.repositories import (
    EditalRepository,
    IESRepository,
    MatchRepository,
    SubscriberRepository,
)
from pos_editais_monitor.infrastructure.db.session import get_session
from pos_editais_monitor.infrastructure.emec.client import EmecClient
from pos_editais_monitor.infrastructure.emec.whitelist import EmecWhitelist
from pos_editais_monitor.infrastructure.llm.anthropic_client import AnthropicLLMClient
from pos_editais_monitor.notifications.dispatcher import (
    DigestItem,
    NotificationDispatcher,
)
from pos_editais_monitor.pipeline.dead_letter import DeadLetterQueue
from pos_editais_monitor.pipeline.orchestrator import PipelineOrchestrator
from pos_editais_monitor.scraping.clients.http_client import HttpClient
from pos_editais_monitor.scraping.clients.playwright_client import PlaywrightClient
from pos_editais_monitor.scraping.spiders import SPIDER_REGISTRY

log = get_logger(__name__)


async def refresh_emec_job() -> int:
    """Carrega/atualiza whitelist de IES em DB. Retorna numero de IES upserted."""
    client = EmecClient()
    count = 0
    async with get_session() as session:
        repo = IESRepository(session)
        async for ies in client.listar_ies_elegiveis():
            await repo.upsert(ies)
            count += 1
    log.info("emec_refreshed", upserted=count)
    return count


async def _build_whitelist() -> EmecWhitelist:
    async with get_session() as session:
        repo = IESRepository(session)
        ies_list = await repo.list_elegiveis()
    return EmecWhitelist(ies_list)


async def run_all_spiders_job() -> None:
    """Roda todos os spiders registrados em sequencia, persistindo + matching."""
    settings = get_settings()
    whitelist = await _build_whitelist()
    if whitelist.size == 0:
        log.warning("whitelist_empty_forcing_refresh")
        await refresh_emec_job()
        whitelist = await _build_whitelist()

    redis = get_redis()
    dlq = DeadLetterQueue(redis)
    llm = AnthropicLLMClient(settings) if settings.llm_enabled else None

    http = HttpClient(settings=settings, redis=redis)
    playwright = PlaywrightClient(settings=settings)
    orchestrator = PipelineOrchestrator(
        whitelist=whitelist,
        dlq=dlq,
        settings=settings,
        llm=llm,
    )

    try:
        for name, cls in SPIDER_REGISTRY.items():
            log.info("spider_dispatch", spider=name)
            spider = cls(http=http, playwright=playwright)
            try:
                await orchestrator.run_spider(spider)
            except Exception:
                log.exception("spider_unexpected_failure", spider=name)
    finally:
        await http.aclose()
        await playwright.aclose()


async def dispatch_digest_job() -> None:
    """Envia digest para cada subscriber com matches pendentes."""
    settings = get_settings()
    dispatcher = NotificationDispatcher(settings=settings)
    today = date.today().isoformat()

    async with get_session() as session:
        sub_repo = SubscriberRepository(session)
        match_repo = MatchRepository(session)
        ed_repo = EditalRepository(session)
        ies_repo = IESRepository(session)

        subscribers = await sub_repo.list_ativos()
        if not subscribers:
            log.info("digest_no_subscribers")
            return

        for profile in subscribers:
            pending = await match_repo.pending_notifications_for(profile.id)
            items: list[DigestItem] = []
            for m in pending:
                edital = await ed_repo.get_by_id(m.edital_id)
                if not edital:
                    continue
                ies = (
                    await ies_repo.get_by_codigo_emec(str(edital.ies_id)) if edital.ies_id else None
                )
                ies_nome = ies.nome if ies else ""
                area = get_by_codigo(edital.area_cnpq_codigo or "")
                area_label = area.nome if area else ""
                items.append(
                    NotificationDispatcher.build_item(
                        edital=edital,
                        ies_nome=ies_nome,
                        area_label=area_label,
                        score=m.score,
                    )
                )

            ok = await dispatcher.send_digest(profile=profile, items=items)
            if ok and pending:
                await match_repo.mark_notified([m.id for m in pending])
                log.info("digest_marked_notified", profile=profile.nome, count=len(pending))
            elif not items:
                log.info("digest_skipped_empty", profile=profile.nome, date=today)
