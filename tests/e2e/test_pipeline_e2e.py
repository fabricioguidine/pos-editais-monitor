"""End-to-end (hermetico) do pipeline parse, classify, match, compose.

Sem rede, sem SMTP, sem banco, sem Docker. Alimenta documentos sinteticos nos
parsers reais e segue exatamente os estagios que o orchestrator usa, parando
antes de qualquer I/O externo. A composicao de email e verificada por uma
captura do payload (nenhum envio ocorre).
"""

from __future__ import annotations

from datetime import date

import pytest

from pos_editais_monitor.domain.entities.edital import Edital
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.matching.engine import MatchEngine
from pos_editais_monitor.notifications.channels.base import NotificationPayload
from pos_editais_monitor.notifications.dispatcher import NotificationDispatcher
from pos_editais_monitor.parsers.html.generic import GenericHtmlParser
from pos_editais_monitor.parsers.pdf.pdf_parser import PdfParser
from pos_editais_monitor.parsers.wordpress.wp_parser import WordPressParser


class _CapturingChannel:
    """Canal fake: captura o payload em vez de enviar. Nenhuma rede ou SMTP."""

    name = "capture"
    enabled = True

    def __init__(self) -> None:
        self.sent: list[NotificationPayload] = []

    async def send(self, payload: NotificationPayload) -> bool:
        self.sent.append(payload)
        return True


@pytest.mark.asyncio
async def test_html_parse_extracts_fields(make_html_response, to_edital) -> None:
    raw = make_html_response("edital_ppgcc_match.html")
    parser = WordPressParser()
    assert parser.can_handle(raw)
    result = await parser.parse(raw)
    e = result.edital
    assert "Mestrado" in e.titulo
    assert "Ciencia da Computacao" in e.titulo
    assert e.nivel is Nivel.MESTRADO_ACADEMICO
    assert e.modalidade is Modalidade.PRESENCIAL
    assert e.periodo_inscricao is not None
    assert e.periodo_inscricao.de == date(2026, 3, 1)
    assert e.periodo_inscricao.ate == date(2026, 4, 15)
    assert e.url_pdf == "https://www.example.com/wp-content/uploads/2026/edital.pdf"
    assert e.confidence > 0.5
    # O WordPressParser nao infere gratuidade; o orchestrator assume gratuito
    # quando o sinal e ausente (None -> True no mapeamento canonico).
    edital = to_edital(e)
    assert edital.is_gratuito is True


@pytest.mark.asyncio
async def test_pdf_parse_extracts_fields(make_pdf_response) -> None:
    raw = make_pdf_response("edital_ppgcc_ufrgs.pdf")
    parser = PdfParser()
    assert parser.can_handle(raw)
    result = await parser.parse(raw)
    e = result.edital
    assert e.extras.get("needs_ocr") is False
    assert "EDITAL" in e.titulo.upper()
    assert e.nivel is Nivel.MESTRADO_ACADEMICO
    assert e.modalidade is Modalidade.PRESENCIAL
    assert e.is_gratuito is True
    assert e.vagas == 25
    assert e.periodo_inscricao is not None
    assert e.periodo_inscricao.de == date(2026, 3, 1)
    assert e.periodo_inscricao.ate == date(2026, 4, 15)


@pytest.mark.asyncio
async def test_generic_html_parser_handles_cross_discipline(make_html_response) -> None:
    raw = make_html_response("edital_geociencias_cross.html", spider="usp-ppg")
    parser = GenericHtmlParser()
    assert parser.can_handle(raw)
    result = await parser.parse(raw)
    e = result.edital
    assert "Geociencias" in e.titulo
    assert e.nivel is Nivel.MESTRADO_ACADEMICO
    assert e.is_gratuito is True
    assert e.periodo_inscricao is not None
    assert e.periodo_inscricao.ate == date(2026, 6, 30)


@pytest.mark.asyncio
async def test_exact_match_is_accepted(make_html_response, to_edital, whitelist, profile) -> None:
    raw = make_html_response("edital_ppgcc_match.html")
    parsed = (await WordPressParser().parse(raw)).edital
    edital = to_edital(parsed)
    assert edital.area_cnpq_codigo == "10300007"
    engine = MatchEngine(whitelist)
    result = engine.evaluate(edital, "UFRGS", profile)
    assert result.matched
    assert result.score >= 1.0


@pytest.mark.asyncio
async def test_cross_discipline_match_is_accepted(
    make_html_response, to_edital, whitelist, profile
) -> None:
    raw = make_html_response("edital_geociencias_cross.html", spider="usp-ppg")
    parsed = (await GenericHtmlParser().parse(raw)).edital
    edital = to_edital(parsed)
    assert edital.area_cnpq_codigo == "10700001"
    engine = MatchEngine(whitelist)
    result = engine.evaluate(edital, "Universidade de Sao Paulo", profile)
    assert result.matched
    assert 0.6 <= result.score <= 0.75


@pytest.mark.asyncio
async def test_paid_course_is_rejected(make_html_response, to_edital, whitelist, profile) -> None:
    raw = make_html_response("edital_pago_reject.html", spider="usp-ppg")
    parsed = (await GenericHtmlParser().parse(raw)).edital
    parsed.is_gratuito = False
    edital = to_edital(parsed)
    engine = MatchEngine(whitelist)
    result = engine.evaluate(edital, "Universidade de Sao Paulo", profile)
    assert not result.matched
    assert any("nao_gratuito" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_ies_outside_whitelist_is_rejected(whitelist, profile) -> None:
    edital = Edital(
        titulo="Mestrado em Ciencia da Computacao",
        nivel=Nivel.MESTRADO_ACADEMICO,
        modalidade=Modalidade.PRESENCIAL,
        area_cnpq_codigo="10300007",
        is_gratuito=True,
    )
    engine = MatchEngine(whitelist)
    result = engine.evaluate(edital, "Faculdade Pirata", profile)
    assert not result.matched
    assert any("ies_fora_whitelist" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_full_pipeline_filters_to_true_matches(
    make_html_response, make_pdf_response, to_edital, whitelist, profile
) -> None:
    documents = [
        (WordPressParser(), make_html_response("edital_ppgcc_match.html"), "UFRGS"),
        (
            GenericHtmlParser(),
            make_html_response("edital_geociencias_cross.html", spider="usp-ppg"),
            "Universidade de Sao Paulo",
        ),
        (PdfParser(), make_pdf_response("edital_ppgcc_ufrgs.pdf"), "UFRGS"),
    ]
    pago_raw = make_html_response("edital_pago_reject.html", spider="usp-ppg")
    engine = MatchEngine(whitelist)
    accepted: list[tuple[Edital, str, float]] = []
    for parser, raw, ies in documents:
        parsed = (await parser.parse(raw)).edital
        edital = to_edital(parsed)
        result = engine.evaluate(edital, ies, profile)
        if result.matched:
            accepted.append((edital, ies, result.score))
    pago_parsed = (await GenericHtmlParser().parse(pago_raw)).edital
    pago_parsed.is_gratuito = False
    pago_result = engine.evaluate(to_edital(pago_parsed), "Universidade de Sao Paulo", profile)
    assert not pago_result.matched
    assert len(accepted) == 3
    assert all(score >= profile.score_minimo for _, _, score in accepted)


@pytest.mark.asyncio
async def test_digest_composition_no_send(profile) -> None:
    capture = _CapturingChannel()
    dispatcher = NotificationDispatcher(channels=[capture])
    edital = Edital(
        titulo="Edital 02/2026 - Mestrado em Ciencia da Computacao",
        nivel=Nivel.MESTRADO_ACADEMICO,
        modalidade=Modalidade.PRESENCIAL,
        area_cnpq_codigo="10300007",
        is_gratuito=True,
        url_origem="https://www.example.com/ppgcc/02-2026",
        url_pdf="https://www.example.com/edital.pdf",
    )
    item = NotificationDispatcher.build_item(
        edital, ies_nome="UFRGS", area_label="Ciencia da Computacao", score=1.0
    )
    ok = await dispatcher.send_digest(profile=profile, items=[item])
    assert ok is True
    assert len(capture.sent) == 1
    payload = capture.sent[0]
    assert payload.recipient == "tester@example.com"
    assert "novo(s) edital(is)" in payload.subject
    assert "Mestrado em Ciencia da Computacao" in payload.body_html
    assert "UFRGS" in payload.body_html
    assert "Ciencia da Computacao" in payload.body_html
    assert "https://www.example.com/edital.pdf" in payload.body_html
    assert "Mestrado em Ciencia da Computacao" in payload.body_text
    assert "UFRGS" in payload.body_text
    assert "Score: 1.00" in payload.body_text


@pytest.mark.asyncio
async def test_digest_skipped_when_no_matches(profile) -> None:
    capture = _CapturingChannel()
    dispatcher = NotificationDispatcher(channels=[capture])
    ok = await dispatcher.send_digest(profile=profile, items=[])
    assert ok is False
    assert capture.sent == []
