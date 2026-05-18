from pos_editais_monitor.domain.entities.ies import IES
from pos_editais_monitor.infrastructure.emec.whitelist import EmecWhitelist


class TestEmecWhitelist:
    def test_lookup_by_sigla(self) -> None:
        wl = EmecWhitelist([IES(codigo_emec="0521", sigla="UFRGS", nome="Universidade Federal do Rio Grande do Sul")])
        assert wl.contains("UFRGS")
        assert wl.contains("ufrgs")

    def test_lookup_by_nome_completo(self) -> None:
        wl = EmecWhitelist([IES(codigo_emec="0578", sigla="USP", nome="Universidade de Sao Paulo")])
        assert wl.contains("Universidade de Sao Paulo")
        assert wl.contains("Universidade de São Paulo")

    def test_substring_match(self) -> None:
        wl = EmecWhitelist([IES(codigo_emec="0578", sigla="USP", nome="Universidade de Sao Paulo")])
        assert wl.contains("USP - Campus Sao Carlos")

    def test_rejects_unknown(self) -> None:
        wl = EmecWhitelist([IES(codigo_emec="0578", sigla="USP", nome="Universidade de Sao Paulo")])
        assert not wl.contains("Faculdade Pirata")

    def test_skips_inelegivel(self) -> None:
        wl = EmecWhitelist(
            [IES(codigo_emec="X", sigla="PAGA", nome="Pos Paga", ativa=False, gratuita=False)]
        )
        assert wl.size == 1
        assert not wl.contains("PAGA")
