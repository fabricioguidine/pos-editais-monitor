"""APScheduler factory.

Jobs registrados:
- refresh_emec     : @ 00:00 diario
- run_all_spiders  : @ 04:00 diario
- dispatch_digest  : @ 07:00 diario  (cron configuravel)
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from pos_editais_monitor.core.config import get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.scheduling.jobs import (
    dispatch_digest_job,
    refresh_emec_job,
    run_all_spiders_job,
)

log = get_logger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    sched = AsyncIOScheduler(timezone="America/Sao_Paulo")

    sched.add_job(refresh_emec_job, CronTrigger.from_crontab("0 0 * * *"), id="refresh_emec")
    sched.add_job(run_all_spiders_job, CronTrigger.from_crontab("0 4 * * *"), id="run_spiders")
    sched.add_job(
        dispatch_digest_job,
        CronTrigger.from_crontab(settings.notify_digest_cron),
        id="dispatch_digest",
    )
    log.info(
        "scheduler_configured",
        refresh_emec="0 0 * * *",
        run_spiders="0 4 * * *",
        dispatch_digest=settings.notify_digest_cron,
    )
    return sched
