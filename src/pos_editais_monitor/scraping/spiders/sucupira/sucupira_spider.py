"""Sucupira spider — catalogo oficial de PPGs reconhecidos pela CAPES.

Spider NAO produz editais. Produz `ParsedEdital` sintetico com nivel=DESCONHECIDO
porem `extras['catalog_only']=True`, indicando que e um PPG descoberto cuja
pagina deve ser visitada por spiders Tier 3 em sprints futuros.

Mais util como **discovery** de fontes secundarias do que como spider em si.

Para MVP, gera 'ParsedEdital'-like com link da pagina do PPG por IES + area,
filtrado por areas-alvo do perfil padrao (CC 1.03 + Geociencias 1.07).
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from urllib.parse import urlencode

from selectolax.parser import HTMLParser

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.scraping.spiders.base.spider import BaseSpider, SpiderContract
from pos_editais_monitor.scraping.types import RawResponse

log = get_logger(__name__)

_SUCUPIRA_BASE = "https://sucupira.capes.gov.br/sucupira/public/consultas/coleta/programa/listaPrograma.jsf"

# Codigos CAPES para grandes areas — alinhados com CNPq mas com leve diferenca
_AREAS_ALVO: list[tuple[str, str]] = [
    ("10300007", "Ciencia da Computacao"),
    ("10700001", "Geociencias"),
]


class SucupiraSpider(BaseSpider):
    name = "sucupira"
    contract = SpiderContract(
        min_bytes=500,
        max_bytes=10_000_000,
        must_contain=("Programa",),
    )

    async def discover_urls(self) -> AsyncIterator[str]:
        for codigo, _nome in _AREAS_ALVO:
            params = {"areaConhecimentoCodigo": codigo}
            yield f"{_SUCUPIRA_BASE}?{urlencode(params)}"

    async def parse_response(self, raw: RawResponse) -> AsyncIterator[ParsedEdital]:
        """Extrai linhas da tabela de programas. Cada linha vira ParsedEdital
        marcado como `catalog_only` — pipeline armazena como sinal/source,
        nao como edital final."""
        tree = HTMLParser(raw.text())
        rows = tree.css("table#listagem tr")
        if not rows:
            # Fallback: padrao alternativo de tabela
            rows = tree.css("tbody tr")
        for tr in rows:
            cells = [c.text(strip=True) for c in tr.css("td")]
            if len(cells) < 4:
                continue
            programa, ies_nome, area, nivel_txt = cells[:4]
            if not programa or not ies_nome:
                continue
            codigo_match = re.search(r"\((\d+)\)", programa)
            codigo_programa = codigo_match.group(1) if codigo_match else ""
            yield ParsedEdital(
                titulo=programa,
                ies_nome=ies_nome,
                fonte_codigo=self.name,
                area_concentracao=area,
                url_origem=raw.url,
                texto_resumo=f"PPG: {programa} - {nivel_txt}",
                confidence=0.9,
                parser_name=self.name,
                extras={
                    "catalog_only": True,
                    "codigo_programa_sucupira": codigo_programa,
                    "nivel_texto": nivel_txt,
                },
            )
