"""LLM fallback para PDF/HTML com baixa confianca."""

from __future__ import annotations

from datetime import date

from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.domain.value_objects.periodo import PeriodoInscricao
from pos_editais_monitor.infrastructure.llm.anthropic_client import AnthropicLLMClient
from pos_editais_monitor.parsers.base import ParseResult

log = get_logger(__name__)


class LLMEditalEnricher:
    """Recebe um ParsedEdital com baixa confianca e tenta enriquecer com LLM.

    Returns a NEW ParsedEdital with merged fields. Em caso de falha do LLM,
    devolve o input intacto.
    """

    def __init__(self, llm: AnthropicLLMClient) -> None:
        self._llm = llm

    async def enrich(self, partial: ParsedEdital) -> ParseResult:
        data = await self._llm.extrair_edital(
            partial.texto_completo or partial.texto_resumo or ""
        )
        if not data:
            return ParseResult(edital=partial, confidence=partial.confidence)

        merged = ParsedEdital(
            titulo=data.get("titulo") or partial.titulo,
            ies_nome=data.get("ies_nome") or partial.ies_nome,
            fonte_codigo=partial.fonte_codigo,
            nivel=_parse_nivel(data.get("nivel")) or partial.nivel,
            modalidade=_parse_modalidade(data.get("modalidade")) or partial.modalidade,
            area_concentracao=data.get("area_concentracao") or partial.area_concentracao,
            is_gratuito=_first_not_none(data.get("is_gratuito"), partial.is_gratuito),
            vagas=_first_not_none(data.get("vagas"), partial.vagas),
            periodo_inscricao=_parse_periodo(data.get("periodo_inscricao"))
            or partial.periodo_inscricao,
            identificador_externo=partial.identificador_externo,
            url_origem=partial.url_origem,
            url_pdf=data.get("link_pdf") or partial.url_pdf,
            texto_resumo=partial.texto_resumo,
            texto_completo=partial.texto_completo,
            confidence=max(partial.confidence, float(data.get("confidence", 0.7))),
            parser_name=f"{partial.parser_name}+llm",
            extras={**partial.extras, "llm_enriched": True},
        )
        return ParseResult(edital=merged, confidence=merged.confidence)


def _first_not_none(*vals):  # type: ignore[no-untyped-def]
    for v in vals:
        if v is not None:
            return v
    return None


def _parse_nivel(s: str | None) -> Nivel | None:
    if not s:
        return None
    try:
        return Nivel(s)
    except ValueError:
        return Nivel.from_text(s)


def _parse_modalidade(s: str | None) -> Modalidade | None:
    if not s:
        return None
    try:
        return Modalidade(s)
    except ValueError:
        return Modalidade.from_text(s)


def _parse_periodo(d: dict | None) -> PeriodoInscricao | None:
    if not d:
        return None
    try:
        de = date.fromisoformat(d["de"]) if d.get("de") else None
        ate = date.fromisoformat(d["ate"]) if d.get("ate") else None
    except (ValueError, TypeError, KeyError):
        return None
    if not de and not ate:
        return None
    return PeriodoInscricao(de=de, ate=ate)
