"""Testes do matching engine — onde precision eh critica."""

from pos_editais_monitor.domain.entities.edital import Edital
from pos_editais_monitor.domain.entities.ies import IES
from pos_editais_monitor.domain.entities.subscriber import (
    AreaAlvo,
    MatchMode,
    SubscriberProfile,
)
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.infrastructure.emec.whitelist import EmecWhitelist
from pos_editais_monitor.matching.engine import MatchEngine


def _build_whitelist() -> EmecWhitelist:
    return EmecWhitelist(
        [
            IES(codigo_emec="0521", sigla="UFRGS", nome="Universidade Federal do Rio Grande do Sul"),
            IES(codigo_emec="0578", sigla="USP", nome="Universidade de Sao Paulo"),
        ]
    )


def _profile_fabricio() -> SubscriberProfile:
    return SubscriberProfile(
        nome="fabricio",
        email="fabricioguidine@gmail.com",
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
        score_minimo=0.70,
    )


class TestMatchEngine:
    def test_exact_match_cc(self) -> None:
        engine = MatchEngine(_build_whitelist())
        edital = Edital(
            titulo="Mestrado em Computacao",
            nivel=Nivel.MESTRADO_ACADEMICO,
            modalidade=Modalidade.PRESENCIAL,
            area_cnpq_codigo="10300007",
            is_gratuito=True,
        )
        result = engine.evaluate(edital, "UFRGS", _profile_fabricio())
        assert result.matched
        assert result.score >= 1.0

    def test_reject_pago(self) -> None:
        engine = MatchEngine(_build_whitelist())
        edital = Edital(
            titulo="MBA em Negocios", area_cnpq_codigo="10300007",
            nivel=Nivel.MBA, modalidade=Modalidade.EAD, is_gratuito=False,
        )
        result = engine.evaluate(edital, "UFRGS", _profile_fabricio())
        assert not result.matched
        assert any("nao_gratuito" in r for r in result.reasons)

    def test_reject_ies_fora_whitelist(self) -> None:
        engine = MatchEngine(_build_whitelist())
        edital = Edital(
            titulo="X", area_cnpq_codigo="10300007",
            nivel=Nivel.MESTRADO_ACADEMICO, modalidade=Modalidade.PRESENCIAL,
            is_gratuito=True,
        )
        result = engine.evaluate(edital, "Faculdade Pirata", _profile_fabricio())
        assert not result.matched
        assert any("ies_fora_whitelist" in r for r in result.reasons)

    def test_cross_discipline_geociencias(self) -> None:
        engine = MatchEngine(_build_whitelist())
        edital = Edital(
            titulo="Mestrado em Geociencias com vagas para Computacao",
            area_cnpq_codigo="10700001",
            nivel=Nivel.MESTRADO_ACADEMICO,
            modalidade=Modalidade.PRESENCIAL,
            is_gratuito=True,
        )
        result = engine.evaluate(edital, "USP", _profile_fabricio())
        assert result.matched
        assert 0.6 <= result.score <= 0.75

    def test_unrelated_area_not_matched(self) -> None:
        engine = MatchEngine(_build_whitelist())
        edital = Edital(
            titulo="Mestrado em Direito Civil",
            area_cnpq_codigo="60100009",
            nivel=Nivel.MESTRADO_ACADEMICO,
            modalidade=Modalidade.PRESENCIAL,
            is_gratuito=True,
        )
        result = engine.evaluate(edital, "USP", _profile_fabricio())
        assert not result.matched
