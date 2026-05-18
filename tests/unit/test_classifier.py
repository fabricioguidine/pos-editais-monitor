from pos_editais_monitor.classification.rules_classifier import RulesClassifier
from pos_editais_monitor.domain.entities.edital import ParsedEdital


def _ed(titulo: str, body: str = "") -> ParsedEdital:
    return ParsedEdital(
        titulo=titulo,
        ies_nome="X",
        fonte_codigo="x",
        texto_resumo=body,
        texto_completo=body,
    )


class TestRulesClassifier:
    def test_computacao(self) -> None:
        c = RulesClassifier().classify(_ed("Mestrado em Ciencia da Computacao", "redes neurais e algoritmos"))
        assert c.area_cnpq_codigo == "10300007"
        assert c.confidence > 0.4

    def test_geociencias(self) -> None:
        c = RulesClassifier().classify(_ed("Mestrado em Geologia", "geofisica e sensoriamento remoto"))
        assert c.area_cnpq_codigo == "10700001"

    def test_no_match(self) -> None:
        c = RulesClassifier().classify(_ed("Doutorado em Filosofia Contemporanea"))
        assert c.area_cnpq_codigo is None
        assert c.confidence == 0.0
