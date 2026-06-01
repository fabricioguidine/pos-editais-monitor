"""Integration-test fixtures.

The DB engine in ``infrastructure.db.session`` is a process-global created
lazily on first use, so it binds to whichever asyncio event loop ran the first
test. pytest-asyncio uses a fresh function-scoped loop per test, so a second
test would reuse an engine attached to a closed loop ("Event loop is closed").
Resetting and disposing the global around each test keeps every test on its
own loop.
"""

from __future__ import annotations

import pytest

from pos_editais_monitor.infrastructure.db import session as db_session


@pytest.fixture(autouse=True)
async def _fresh_db_engine():
    db_session._engine = None
    db_session._session_factory = None
    yield
    engine = db_session._engine
    if engine is not None:
        await engine.dispose()
    db_session._engine = None
    db_session._session_factory = None
