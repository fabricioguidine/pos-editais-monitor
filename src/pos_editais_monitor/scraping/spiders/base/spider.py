"""BaseSpider — interface comum.

Cada spider implementa:
- `name`: identificador unico no registry
- `discover_urls()`: gera URLs a serem fetched
- `parse_response(raw)`: produz `ParsedEdital` (1..N)

O orchestrator consome esses generators async sem precisar conhecer detalhes
de cada fonte.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.core.observability import METRICS
from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.scraping.clients.http_client import HttpClient
from pos_editais_monitor.scraping.clients.playwright_client import PlaywrightClient
from pos_editais_monitor.scraping.errors import ContractViolationError
from pos_editais_monitor.scraping.types import FetchRequest, RawResponse

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SpiderContract:
    """Assercoes sobre a resposta — falhar = drift no upstream."""

    min_bytes: int = 100
    max_bytes: int = 5_000_000
    must_contain: tuple[str, ...] = field(default_factory=tuple)


class BaseSpider(ABC):
    name: str = "base"
    contract: SpiderContract = SpiderContract()
    prefer_rss: bool = False
    use_playwright: bool = False

    def __init__(
        self,
        http: HttpClient,
        playwright: PlaywrightClient | None = None,
    ) -> None:
        self._http = http
        self._playwright = playwright

    @abstractmethod
    def discover_urls(self) -> AsyncIterator[str]:
        """Iterador de URLs candidatas. Pode paginar internamente."""
        raise NotImplementedError

    @abstractmethod
    async def parse_response(self, raw: RawResponse) -> AsyncIterator[ParsedEdital]:
        """Parser proprio do spider. Pode delegar para parsers/."""
        raise NotImplementedError

    async def fetch(self, url: str) -> RawResponse:
        req = FetchRequest(url=url, spider=self.name)
        if self.use_playwright and self._playwright is not None:
            return await self._playwright.fetch(url, spider=self.name)
        raw = await self._http.fetch(req)
        self._assert_contract(raw)
        return raw

    def _assert_contract(self, raw: RawResponse) -> None:
        size = len(raw.body)
        if size < self.contract.min_bytes:
            METRICS.spider_contract_violations_total.labels(self.name, "too_small").inc()
            raise ContractViolationError(f"{self.name}: body too small ({size}b)")
        if size > self.contract.max_bytes:
            METRICS.spider_contract_violations_total.labels(self.name, "too_large").inc()
            raise ContractViolationError(f"{self.name}: body too large ({size}b)")
        if self.contract.must_contain:
            text = raw.body[: 50_000].decode("utf-8", errors="ignore").lower()
            for token in self.contract.must_contain:
                if token.lower() not in text:
                    METRICS.spider_contract_violations_total.labels(
                        self.name, f"missing:{token}"
                    ).inc()
                    raise ContractViolationError(
                        f"{self.name}: response missing required token '{token}'"
                    )
