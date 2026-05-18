"""DOU spider — Imprensa Nacional / Diario Oficial da Uniao.

Estrategia: usar a API JSON publica de busca do `in.gov.br/leiturajornal`.
Filtramos por termos relacionados a editais de pos-graduacao.

Note: a API real do DOU passou por mudancas; mantemos o spider robusto a
schema drift e com contract assertions.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date, timedelta
from urllib.parse import urlencode

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.scraping.spiders.base.spider import BaseSpider, SpiderContract
from pos_editais_monitor.scraping.types import RawResponse

log = get_logger(__name__)

# Termos buscados na API de pesquisa. Conservadores para alta precisao.
_TERMOS_BUSCA = [
    "edital pos-graduacao",
    "processo seletivo mestrado",
    "processo seletivo doutorado",
    "chamada publica especializacao",
    "edital programa de pos-graduacao",
]

_API_BASE = "https://www.in.gov.br/consulta/-/buscar/dou"


class DouSpider(BaseSpider):
    name = "dou"
    contract = SpiderContract(
        min_bytes=100,
        max_bytes=10_000_000,
        # Resposta JSON da pesquisa — esperamos pelo menos a chave 'items'
        must_contain=("items",),
    )

    async def discover_urls(self) -> AsyncIterator[str]:
        """Gera URLs de busca para os ultimos 7 dias e termos relevantes."""
        hoje = date.today()
        de = (hoje - timedelta(days=7)).strftime("%d-%m-%Y")
        ate = hoje.strftime("%d-%m-%Y")
        for termo in _TERMOS_BUSCA:
            params = {
                "q": termo,
                "delta": "ate",
                "publicadoDe": de,
                "publicadoAte": ate,
                "currentPage": "1",
                "rowsPerPage": "50",
            }
            yield f"{_API_BASE}?{urlencode(params)}"

    async def parse_response(self, raw: RawResponse) -> AsyncIterator[ParsedEdital]:
        """Parser tolerante a schema drift.

        DOU oficialmente serve HTML, mas alguns endpoints retornam JSON.
        Esta implementacao trata os dois — em producao, refinamos conforme
        observamos o formato real.
        """
        text = raw.text()
        items: list[dict] = []
        if raw.content_type.startswith("application/json"):
            try:
                payload = json.loads(text)
                items = payload.get("items", []) or payload.get("hits", [])
            except json.JSONDecodeError as exc:
                log.warning("dou_invalid_json", err=str(exc))
                return
        else:
            # Fallback HTML — extrai links de detalhamento como heuristica
            from selectolax.parser import HTMLParser
            tree = HTMLParser(text)
            for a in tree.css("a.resultado"):
                href = a.attributes.get("href", "")
                titulo = (a.text(strip=True) or "")[:512]
                if href and titulo:
                    items.append({"urlTitulo": href, "title": titulo})

        for item in items:
            titulo = (item.get("title") or item.get("titulo") or "").strip()
            url = (item.get("urlTitulo") or item.get("url") or "").strip()
            if not (titulo and url):
                continue
            yield ParsedEdital(
                titulo=titulo,
                ies_nome=item.get("orgao", "Diario Oficial da Uniao"),
                fonte_codigo=self.name,
                nivel=Nivel.from_text(titulo),
                url_origem=url if url.startswith("http") else f"https://www.in.gov.br{url}",
                texto_resumo=(item.get("ementa") or "")[:1000],
                texto_completo=item.get("conteudo", ""),
                confidence=0.5,   # baixa: DOU eh ementa, precisa enriquecer
                parser_name=self.name,
                extras={"dou_secao": item.get("secao"), "publicado_em": item.get("pubDate")},
            )
