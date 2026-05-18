from datetime import date

import pytest

from pos_editais_monitor.parsers.fields.dates import extract_periodo_inscricao


class TestExtractPeriodoInscricao:
    def test_range_ddmmyyyy(self) -> None:
        p = extract_periodo_inscricao(
            "Periodo de inscricao: de 01/03/2026 a 15/04/2026."
        )
        assert p is not None
        assert p.de == date(2026, 3, 1)
        assert p.ate == date(2026, 4, 15)

    def test_only_ate_with_keyword(self) -> None:
        p = extract_periodo_inscricao("Prazo: ate 30/06/2026")
        assert p is not None
        assert p.de is None
        assert p.ate == date(2026, 6, 30)

    def test_br_long_format(self) -> None:
        p = extract_periodo_inscricao(
            "As inscricoes vao de 1 de marco de 2026 a 15 de abril de 2026."
        )
        assert p is not None
        assert p.de == date(2026, 3, 1)
        assert p.ate == date(2026, 4, 15)

    def test_invalid_dates_ignored(self) -> None:
        p = extract_periodo_inscricao("Inscricoes 30/02/2026")
        # 30 de fev nao existe; devolve None
        assert p is None or p.de != date(2026, 2, 30)

    def test_empty(self) -> None:
        assert extract_periodo_inscricao("") is None

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Inscricoes 01/12/2026", date(2026, 12, 1)),
            ("Inscricoes 1 de dezembro de 2026", date(2026, 12, 1)),
        ],
    )
    def test_single_date_default_de(self, text: str, expected: date) -> None:
        p = extract_periodo_inscricao(text)
        assert p is not None
        assert p.de == expected
