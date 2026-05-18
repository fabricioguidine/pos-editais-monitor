"""Smoke test do schema/DB. Requer PG + alembic upgrade head."""

import pytest
from sqlalchemy import text

from pos_editais_monitor.infrastructure.db.session import get_session


@pytest.mark.integration
@pytest.mark.asyncio
async def test_select_one() -> None:
    async with get_session() as s:
        result = await s.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tables_present() -> None:
    async with get_session() as s:
        result = await s.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN "
                "('ies','fontes','editais','snapshots','subscribers','match_records')"
            )
        )
        assert result.scalar_one() == 6
