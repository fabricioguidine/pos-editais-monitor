"""Fixtures globais."""

from __future__ import annotations

from pathlib import Path

import pytest

from pos_editais_monitor.core.logging import configure_logging

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def _logging() -> None:
    configure_logging(level="WARNING", fmt="console")


@pytest.fixture
def html_fixture():
    def _load(name: str) -> bytes:
        return (_FIXTURES / "html" / name).read_bytes()

    return _load


@pytest.fixture
def pdf_fixture():
    def _load(name: str) -> bytes:
        return (_FIXTURES / "pdf" / name).read_bytes()

    return _load
