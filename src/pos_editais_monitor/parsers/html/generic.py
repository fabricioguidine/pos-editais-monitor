"""Parser HTML generico — usado como fallback no registry.

Estrategia:
- Extrai <title> e <h1> para titulo
- Procura por palavras-chave no body (nivel, modalidade, vagas)
- Confidence baseada em quantos campos foram extraidos
"""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser

from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.parsers.base import ParseResult
from pos_editais_monitor.parsers.fields.dates import extract_periodo_inscricao
from pos_editais_monitor.parsers.fields.normalize import normalize_text
from pos_editais_monitor.scraping.types import RawResponse

_VAGAS_RE = re.compile(r"(\d+)\s+vagas?", re.IGNORECASE)
_GRATUITO_HINT = re.compile(
    r"\b(gratuit[ao]|sem\s+custo|sem\s+\w+\s+mensalidad|publico)\b", re.IGNORECASE
)


class GenericHtmlParser:
    name = "html_generic"

    def can_handle(self, raw: RawResponse) -> bool:
        return raw.is_html

    async def parse(self, raw: RawResponse) -> ParseResult:
        text = raw.text()
        tree = HTMLParser(text)
        title = ""
        if tree.css_first("title"):
            title = tree.css_first("title").text(strip=True)  # type: ignore[union-attr]
        h1 = tree.css_first("h1")
        if h1 and h1.text(strip=True):
            title = h1.text(strip=True)
        title = normalize_text(title)[:512]

        # Texto plano para extracao de campos
        body_node = tree.css_first("main") or tree.css_first("article") or tree.body
        body_text = body_node.text(strip=True) if body_node else text
        body_norm = normalize_text(body_text)[:30000]

        nivel = Nivel.from_text(body_norm[:2000], title=title)
        modalidade = Modalidade.from_text(body_norm[:5000])

        vagas_m = _VAGAS_RE.search(body_norm)
        vagas = int(vagas_m.group(1)) if vagas_m else None

        is_gratuito: bool | None = None
        if _GRATUITO_HINT.search(body_norm):
            is_gratuito = True

        periodo = extract_periodo_inscricao(body_norm)

        # Heuristica: PDF embed?
        pdf_link = None
        for a in tree.css("a[href$='.pdf']"):
            pdf_link = a.attributes.get("href")
            if pdf_link:
                break

        # Confidence: 0.2 base + 0.1 por campo extraido
        score = 0.2
        for v in (title, vagas, periodo, pdf_link):
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
            fonte_codigo=raw.spider or "html_generic",
            nivel=nivel,
            modalidade=modalidade,
            vagas=vagas,
            is_gratuito=is_gratuito,
            periodo_inscricao=periodo,
            url_origem=raw.final_url,
            url_pdf=pdf_link,
            texto_resumo=body_norm[:1000],
            texto_completo=body_norm,
            confidence=score,
            parser_name=self.name,
        )
        return ParseResult(edital=edital, confidence=score)
