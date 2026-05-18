"""Circuit breaker por host - protege upstream e nos protege."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.scraping.errors import CircuitOpenError

log = get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _CircuitWindow:
    state: CircuitState = CircuitState.CLOSED
    failures: list[float] = field(default_factory=list)
    opened_at: float | None = None


class CircuitBreaker:
    """Estado em memoria (por processo). Para deploy multi-worker, mover para Redis."""

    def __init__(
        self,
        failure_window_seconds: int = 60,
        failure_threshold: int = 3,
        cooldown_seconds: int = 300,
    ) -> None:
        self._window_s = failure_window_seconds
        self._threshold = failure_threshold
        self._cooldown_s = cooldown_seconds
        self._hosts: dict[str, _CircuitWindow] = {}

    def check(self, url: str) -> None:
        host = urlparse(url).hostname or "unknown"
        w = self._hosts.get(host)
        if not w:
            return
        if w.state is CircuitState.OPEN:
            assert w.opened_at is not None
            if time.time() - w.opened_at >= self._cooldown_s:
                w.state = CircuitState.HALF_OPEN
                log.info("circuit_half_open", host=host)
                return
            raise CircuitOpenError(f"Circuit OPEN for host={host}")

    def record_success(self, url: str) -> None:
        host = urlparse(url).hostname or "unknown"
        w = self._hosts.get(host)
        if not w:
            return
        if w.state in (CircuitState.OPEN, CircuitState.HALF_OPEN):
            log.info("circuit_closed", host=host)
        w.state = CircuitState.CLOSED
        w.failures.clear()
        w.opened_at = None

    def record_failure(self, url: str) -> None:
        host = urlparse(url).hostname or "unknown"
        w = self._hosts.setdefault(host, _CircuitWindow())
        now = time.time()
        w.failures = [t for t in w.failures if now - t <= self._window_s]
        w.failures.append(now)
        if w.state is CircuitState.HALF_OPEN:
            w.state = CircuitState.OPEN
            w.opened_at = now
            log.warning("circuit_reopen", host=host)
            return
        if len(w.failures) >= self._threshold:
            w.state = CircuitState.OPEN
            w.opened_at = now
            log.warning(
                "circuit_open",
                host=host,
                failures=len(w.failures),
                window_s=self._window_s,
            )
