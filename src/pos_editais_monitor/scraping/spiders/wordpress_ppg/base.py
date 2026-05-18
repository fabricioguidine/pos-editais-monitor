"""Spider WordPress generico para PPGs.

Estrategia:
- discover_urls yields o feed RSS (1 URL) OU a pagina de listagem (fallback)
- parse_response:
  - Se for XML/RSS: itera items, filtra por titulo (so editais), produz ParsedEdital
  - Se for HTML: usa WordPressParser do parsers/
- Filtro de relevancia por keywords no titulo: edital | processo seletivo | inscricao | chamada
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

from lxml import etree
from selectolax.parser import HTMLParser

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.parsers.fields.dates import extract_periodo_inscricao
from pos_editais_monitor.parsers.fields.normalize import normalize_text
from pos_editais_monitor.scraping.spiders.base.spider import BaseSpider, SpiderContract
from pos_editais_monitor.scraping.types import RawResponse

log = get_logger(__name__)

_RELEVANCE_RE = re.compile(
    r"\b("
    r"edital|"
    r"processo\s+seletivo|"
    r"inscri[cç][aã]o|"
    r"chamada|"                          # CPNU/APO usam 'Primeira Chamada'
    r"sele[cç][aã]o|"
    r"especializa[cç][aã]o|"
    r"\bmba\b|"
    r"p[oó]s[\s-]graduacao|"
    r"forma[cç][aã]o|"
    r"capacita[cç][aã]o"
    r")\b",
    re.IGNORECASE,
)


class PPGWordPressSpider(BaseSpider):
    """Base para PPGs em WordPress. Subclasses configuram URLs e nome de IES."""

    name: str = "wp-ppg-base"
    ies_nome: str = ""
    feed_url: str | None = None       # se setado, prefer RSS-first
    listing_url: str = ""             # fallback HTML
    contract = SpiderContract(min_bytes=200, max_bytes=10_000_000)

    async def discover_urls(self) -> AsyncIterator[str]:
        if self.feed_url:
            yield self.feed_url
            return
        if self.listing_url:
            yield self.listing_url
            return
        log.warning("ppg_no_urls_configured", spider=self.name)

    async def parse_response(self, raw: RawResponse) -> AsyncIterator[ParsedEdital]:
        if raw.is_xml_or_rss or raw.body.lstrip().startswith(b"<?xml"):
            async for ed in self._parse_rss(raw):
                yield ed
            return
        if raw.is_html:
            async for ed in self._parse_html_listing(raw):
                yield ed
            return
        log.warning("ppg_unknown_content_type", ct=raw.content_type, url=raw.url)

    # ----- RSS path ---------------------------------------------------------

    async def _parse_rss(self, raw: RawResponse) -> AsyncIterator[ParsedEdital]:
        """Parse RSS 2.0 com lxml. Trata namespaces (content:, dc:, etc.)."""
        try:
            root = etree.fromstring(raw.body, parser=etree.XMLParser(recover=True))
        except etree.XMLSyntaxError as exc:
            log.warning("rss_xml_invalid", err=str(exc), spider=self.name)
            return
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
        items = root.findall(".//item")
        emitted = 0
        for item in items:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            content_el = item.find("content:encoded", ns)

            title = normalize_text((title_el.text or "") if title_el is not None else "")
            if not title or not _RELEVANCE_RE.search(title):
                continue
            link = (link_el.text or "").strip() if link_el is not None else ""
            raw_desc = ""
            if content_el is not None and content_el.text:
                raw_desc = content_el.text
            elif desc_el is not None and desc_el.text:
                raw_desc = desc_el.text
            description = re.sub(r"<[^>]+>", " ", raw_desc)
            description = normalize_text(description)[:5000]

            nivel = Nivel.from_text(description[:1000], title=title)
            modalidade = Modalidade.from_text(title + " " + description[:3000])
            if modalidade is Modalidade.DESCONHECIDA:
                modalidade = Modalidade.PRESENCIAL   # default razoavel para PPG
            periodo = extract_periodo_inscricao(description)

            yield ParsedEdital(
                titulo=title,
                ies_nome=self.ies_nome,
                fonte_codigo=self.name,
                nivel=nivel,
                modalidade=modalidade,
                is_gratuito=True,
                periodo_inscricao=periodo,
                url_origem=link,
                texto_resumo=description[:1000],
                texto_completo=description,
                confidence=0.55 if periodo else 0.40,
                parser_name=f"{self.name}+rss",
            )
            emitted += 1
            if emitted >= 20:
                break

    # ----- HTML listing path -----------------------------------------------

    async def _parse_html_listing(self, raw: RawResponse) -> AsyncIterator[ParsedEdital]:
        """Fallback HTML em dois estagios:
        1. WP padrao: <article>/.post/.entry com titulo em <h2 a>
        2. Generico: qualquer <a> cujo texto contem palavra-chave de relevancia
        """
        tree = HTMLParser(raw.text())
        articles = tree.css("article") or tree.css(".post") or tree.css(".entry")
        emitted = 0

        # ---- Estagio 1: WP padrao ----
        for art in articles:
            title_node = art.css_first(".entry-title a") or art.css_first("h2 a") or art.css_first("h1 a")
            if not title_node:
                continue
            title = normalize_text(title_node.text(strip=True))
            if not _RELEVANCE_RE.search(title):
                continue
            link = title_node.attributes.get("href", "")
            excerpt_node = art.css_first(".entry-summary") or art.css_first(".excerpt") or art.css_first("p")
            excerpt = normalize_text(excerpt_node.text(strip=True)) if excerpt_node else ""

            nivel = Nivel.from_text(excerpt[:1000], title=title)
            modalidade = Modalidade.from_text(excerpt[:2000])
            periodo = extract_periodo_inscricao(excerpt)

            yield ParsedEdital(
                titulo=title,
                ies_nome=self.ies_nome,
                fonte_codigo=self.name,
                nivel=nivel,
                modalidade=modalidade,
                is_gratuito=True,
                periodo_inscricao=periodo,
                url_origem=link or raw.final_url,
                texto_resumo=excerpt[:1000],
                texto_completo=excerpt,
                confidence=0.45 if periodo else 0.30,
                parser_name=f"{self.name}+html-listing",
            )
            emitted += 1
            if emitted >= 20:
                break

        if emitted > 0:
            return

        # ---- Estagio 2: fallback generico por keyword em <a> ----
        # Para sites que nao usam <article>. Coleta todos os <a> com texto
        # contendo palavra-chave de relevancia, deduplica por URL.
        from urllib.parse import urljoin

        seen_urls: set[str] = set()
        base = raw.final_url or raw.url
        for a in tree.css("a"):
            href = a.attributes.get("href", "") or ""
            text = normalize_text(a.text(strip=True))
            if not href or not text:
                continue
            if not _RELEVANCE_RE.search(text):
                continue
            if len(text) < 8 or len(text) > 200:
                continue
            full_url = urljoin(base, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            nivel = Nivel.from_text(text, title=text)
            modalidade = Modalidade.from_text(text)
            yield ParsedEdital(
                titulo=text[:512],
                ies_nome=self.ies_nome,
                fonte_codigo=self.name,
                nivel=nivel,
                modalidade=modalidade,
                is_gratuito=True,
                url_origem=full_url,
                texto_resumo=text[:1000],
                texto_completo=text,
                confidence=0.35,
                parser_name=f"{self.name}+keyword-links",
            )
            emitted += 1
            if emitted >= 20:
                break
