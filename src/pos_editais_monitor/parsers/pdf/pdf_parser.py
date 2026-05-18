"""Parser de PDF — pdfplumber + heuristicas + fallback LLM.

Fluxo:
1. Extrai texto via pdfplumber (preserva layout)
2. Limpa headers/footers (linhas repetidas em muitas paginas)
3. Aplica regex/heuristicas para campos
4. Calcula confidence. Se < threshold, sinaliza fallback LLM (caller decide)
"""

from __future__ import annotations

import io
import re
from collections import Counter

import pdfplumber

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.parsers.base import ParseResult
from pos_editais_monitor.parsers.fields.dates import extract_periodo_inscricao
from pos_editais_monitor.parsers.fields.normalize import normalize_text
from pos_editais_monitor.scraping.types import RawResponse

log = get_logger(__name__)

_VAGAS_RE = re.compile(r"(\d{1,3})\s+vagas?", re.IGNORECASE)
_GRATUITO_RE = re.compile(r"\b(gratuit[oa]|sem\s+\w+\s+mensalidad|isent[oa])\b", re.IGNORECASE)
_TITULO_RE = re.compile(
    r"EDITAL\s+N[ºo°]?\s*\d+\s*/?\s*\d{2,4}[^\n]{0,200}", re.IGNORECASE
)


class PdfParser:
    name = "pdf"
    needs_ocr_min_chars: int = 100   # se texto extraido < isso, marca como needs_ocr

    def can_handle(self, raw: RawResponse) -> bool:
        return raw.is_pdf

    async def parse(self, raw: RawResponse) -> ParseResult:
        text = self._extract_text(raw.body)
        normalized = normalize_text(text)
        needs_ocr = len(normalized) < self.needs_ocr_min_chars

        title = ""
        if (m := _TITULO_RE.search(normalized)):
            title = m.group(0).strip()[:512]
        elif normalized:
            # primeira linha "interessante" como fallback
            first = next(
                (line for line in normalized.split(". ") if len(line) > 20),
                "(sem titulo)",
            )
            title = first[:512]

        nivel = Nivel.from_text(normalized[:2000], title=title)
        modalidade = Modalidade.from_text(normalized[:5000])
        periodo = extract_periodo_inscricao(normalized)

        vagas_m = _VAGAS_RE.search(normalized)
        vagas = int(vagas_m.group(1)) if vagas_m else None
        is_gratuito = bool(_GRATUITO_RE.search(normalized))

        # Confidence
        score = 0.1 if needs_ocr else 0.3
        for v in (title, vagas, periodo):
            if v:
                score += 0.12
        if nivel is not Nivel.DESCONHECIDO:
            score += 0.1
        if modalidade is not Modalidade.DESCONHECIDA:
            score += 0.1
        score = min(score, 0.95)

        edital = ParsedEdital(
            titulo=title or "(sem titulo)",
            ies_nome="",
            fonte_codigo=raw.spider or "pdf",
            nivel=nivel,
            modalidade=modalidade,
            vagas=vagas,
            is_gratuito=is_gratuito or None,
            periodo_inscricao=periodo,
            url_origem=raw.final_url,
            url_pdf=raw.final_url,
            texto_resumo=normalized[:1000],
            texto_completo=normalized,
            confidence=score,
            parser_name=self.name,
            extras={"needs_ocr": needs_ocr},
        )
        return ParseResult(edital=edital, confidence=score)

    def _extract_text(self, body: bytes) -> str:
        try:
            with pdfplumber.open(io.BytesIO(body)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
        except Exception as exc:
            log.warning("pdf_extract_failed", err=str(exc))
            return ""
        return self._strip_repeated_lines(pages_text)

    @staticmethod
    def _strip_repeated_lines(pages: list[str]) -> str:
        """Remove linhas que aparecem em >50% das paginas (provavelmente
        header/footer)."""
        if not pages:
            return ""
        counter: Counter[str] = Counter()
        lines_per_page = []
        for p in pages:
            lines = [normalize_text(line) for line in p.splitlines() if line.strip()]
            lines_per_page.append(lines)
            counter.update(set(lines))
        threshold = max(2, len(pages) // 2 + 1)
        repeated = {line for line, n in counter.items() if n >= threshold and len(line) < 80}
        kept = []
        for lines in lines_per_page:
            kept.extend(line for line in lines if line not in repeated)
        return "\n".join(kept)
