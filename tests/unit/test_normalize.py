from pos_editais_monitor.parsers.fields.normalize import normalize_text, normalize_to_ascii


class TestNormalizeText:
    def test_collapses_whitespace(self) -> None:
        assert normalize_text("foo   bar\n\nbaz") == "foo bar baz"

    def test_removes_zero_width(self) -> None:
        assert normalize_text("foo​bar") == "foobar"

    def test_handles_empty(self) -> None:
        assert normalize_text("") == ""
        assert normalize_text(None) == ""  # type: ignore[arg-type]


class TestNormalizeToAscii:
    def test_strips_accents(self) -> None:
        assert normalize_to_ascii("Ciência da Computação") == "ciencia da computacao"

    def test_lowercase(self) -> None:
        assert normalize_to_ascii("UFRGS") == "ufrgs"
