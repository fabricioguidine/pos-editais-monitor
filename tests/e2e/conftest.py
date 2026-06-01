"""Fixtures hermeticas para a suite end-to-end.

Nada aqui toca rede, SMTP, banco ou Docker. Documentos sinteticos (HTML/PDF)
em tests/fixtures sao alimentados nos parsers reais; o resultado segue pelo
mesmo mapeamento ParsedEdital->Edital usado pelo orchestrator, pelo matching
engine e pela composicao de digest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pos_editais_monitor.classification.rules_classifier import RulesClassifier
from pos_editais_monitor.domain.entities.edital import Edital, ParsedEdital
from pos_editais_monitor.domain.entities.ies import IES
from pos_editais_monitor.domain.entities.subscriber import (
    AreaAlvo,
    MatchMode,
    SubscriberProfile,
)
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.infrastructure.emec.whitelist import EmecWhitelist
from pos_editais_monitor.scraping.types import RawResponse

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def make_html_response():
    """Constroi um RawResponse HTML a partir de um arquivo de fixture."""

    def _make(name: str, *, spider: str = "ufrgs-ppg", url: str | None = None) -> RawResponse:
        body = (_FIXTURES / "html" / name).read_bytes()
        u = url or f"https://www.example.com/{name}"
        return RawResponse(
            url=u,
            final_url=u,
            status=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=body,
            spider=spider,
        )

    return _make


@pytest.fixture
def make_pdf_response():
    """Constroi um RawResponse PDF a partir de um arquivo de fixture."""

    def _make(name: str, *, spider: str = "dou", url: str | None = None) -> RawResponse:
        body = (_FIXTURES / "pdf" / name).read_bytes()
        u = url or f"https://www.example.com/{name}"
        return RawResponse(
            url=u,
            final_url=u,
            status=200,
            headers={"content-type": "application/pdf"},
            body=body,
            spider=spider,
        )

    return _make


@pytest.fixture
def classifier() -> RulesClassifier:
    return RulesClassifier()


@pytest.fixture
def whitelist() -> EmecWhitelist:
    return EmecWhitelist(
        [
            IES(
                codigo_emec="0521",
                sigla="UFRGS",
                nome="Universidade Federal do Rio Grande do Sul",
            ),
            IES(codigo_emec="0578", sigla="USP", nome="Universidade de Sao Paulo"),
        ]
    )


@pytest.fixture
def profile() -> SubscriberProfile:
    """Perfil sintetico: CC exato + Geociencias cross-discipline."""
    return SubscriberProfile(
        nome="tester",
        email="tester@example.com",
        formacao="bacharelado_ciencia_computacao",
        areas_alvo=[
            AreaAlvo(codigo_cnpq="10300007", modo=MatchMode.EXACT, peso=1.0),
            AreaAlvo(
                codigo_cnpq="10700001",
                modo=MatchMode.CROSS_DISCIPLINE,
                peso=0.7,
                requer_aceita_cs=True,
            ),
        ],
        niveis_aceitos={Nivel.MESTRADO_ACADEMICO, Nivel.MESTRADO_PROFISSIONAL, Nivel.DOUTORADO},
        score_minimo=0.70,
    )


@pytest.fixture
def to_edital(classifier: RulesClassifier):
    """Mapeia ParsedEdital -> Edital + classifica area, como o orchestrator faz."""

    def _convert(parsed: ParsedEdital) -> Edital:
        cls = classifier.classify(parsed)
        if cls.area_cnpq_codigo:
            parsed.area_cnpq_codigo = cls.area_cnpq_codigo
        return Edital(
            titulo=parsed.titulo,
            nivel=parsed.nivel,
            modalidade=parsed.modalidade,
            area_cnpq_codigo=parsed.area_cnpq_codigo,
            is_gratuito=bool(parsed.is_gratuito) if parsed.is_gratuito is not None else True,
            vagas=parsed.vagas,
            periodo_inscricao=parsed.periodo_inscricao,
            url_origem=parsed.url_origem,
            url_pdf=parsed.url_pdf,
            texto_resumo=parsed.texto_resumo,
        )

    return _convert
