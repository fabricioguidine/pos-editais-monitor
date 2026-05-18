"""Parser para sites WordPress (padrao comum em PPGs).

Heuristicas:
- <article class="post"> ou .entry-content como container do conteudo
- Categorias/tags em <a rel="category tag">
- PDF link em <a href="...wp-content/uploads/.../edital.pdf">
"""

from __future__ import annotations

from selectolax.parser import HTMLParser

from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.parsers.base import ParseResult
from pos_editais_monitor.parsers.fields.dates import extract_periodo_inscricao
from pos_editais_monitor.parsers.fields.normalize import normalize_text
from pos_editais_monitor.scraping.types import RawResponse


class WordPressParser:
    name = "wordpress"

    def can_handle(self, raw: RawResponse) -> bool:
        if not raw.is_html:
            return False
        body_head = raw.body[:8000].decode("utf-8", errors="ignore").lower()
        return "wp-content" in body_head or 'generator" content="wordpress' in body_head

    async def parse(self, raw: RawResponse) -> ParseResult:
        tree = HTMLParser(raw.text())
        # Titulo: prefere .entry-title
        title_node = tree.css_first(".entry-title") or tree.css_first("h1")
        title = normalize_text(title_node.text(strip=True))[:512] if title_node else ""

        content_node = (
            tree.css_first(".entry-content")
            or tree.css_first("article")
            or tree.css_first("main")
        )
        body_text = normalize_text(content_node.text(strip=True)) if content_node else ""
        body_text = body_text[:30000]

        nivel = Nivel.from_text(body_text[:2000], title=title)
        modalidade = Modalidade.from_text(body_text[:5000])
        periodo = extract_periodo_inscricao(body_text)

        pdf_link = None
        if content_node:
            for a in content_node.css("a[href*='wp-content/uploads']"):
                href = a.attributes.get("href")
                if href and href.endswith(".pdf"):
                    pdf_link = href
                    break

        score = 0.4   # WP tem estrutura mais previsivel, baseline maior
        for v in (title, periodo, pdf_link):
            if v:
                score += 0.1
        if nivel is not Nivel.DESCONHECIDO:
            score += 0.1
        if modalidade is not Modalidade.DESCONHECIDA:
            score += 0.1
        score = min(score, 0.95)

        edital = ParsedEdital(
            titulo=title or "(sem titulo)",
            ies_nome="",
            fonte_codigo=raw.spider or "wordpress",
            nivel=nivel,
            modalidade=modalidade,
            periodo_inscricao=periodo,
            url_origem=raw.final_url,
            url_pdf=pdf_link,
            texto_resumo=body_text[:1000],
            texto_completo=body_text,
            confidence=score,
            parser_name=self.name,
        )
        return ParseResult(edital=edital, confidence=score)
