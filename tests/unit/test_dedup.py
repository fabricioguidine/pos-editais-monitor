from pos_editais_monitor.dedup.canonical_hash import canonical_hash
from pos_editais_monitor.dedup.change_detector import ChangeDetector, ChangeKind
from pos_editais_monitor.dedup.simhash import compute_simhash, hamming_distance
from pos_editais_monitor.domain.entities.edital import Edital, ParsedEdital
from pos_editais_monitor.domain.enums.nivel import Nivel


class TestCanonicalHash:
    def test_same_input_same_hash(self) -> None:
        p1 = ParsedEdital(titulo="Edital X", ies_nome="UFRGS", fonte_codigo="ufrgs", nivel=Nivel.MESTRADO_ACADEMICO)
        p2 = ParsedEdital(titulo="Edital X", ies_nome="UFRGS", fonte_codigo="ufrgs", nivel=Nivel.MESTRADO_ACADEMICO)
        assert canonical_hash(p1) == canonical_hash(p2)

    def test_whitespace_and_accent_invariant(self) -> None:
        p1 = ParsedEdital(titulo="Pos em Geocincias", ies_nome="UFRGS", fonte_codigo="x")
        p2 = ParsedEdital(titulo="Pos em Geocincias  ", ies_nome="ufrgs", fonte_codigo="x")
        # Titulo igual modulo whitespace + ies case-invariant via normalize_to_ascii
        # Hashes podem diferir se whitespace nao for normalizado no titulo input;
        # nesta forma canonical normaliza, portanto iguais:
        assert canonical_hash(p1) == canonical_hash(p2)

    def test_diff_fonte_diff_hash(self) -> None:
        p1 = ParsedEdital(titulo="X", ies_nome="UFRGS", fonte_codigo="ufrgs")
        p2 = ParsedEdital(titulo="X", ies_nome="UFRGS", fonte_codigo="capes")
        assert canonical_hash(p1) != canonical_hash(p2)


class TestSimhash:
    def test_identical(self) -> None:
        a = compute_simhash("Edital de Mestrado em Computacao Cientifica")
        b = compute_simhash("Edital de Mestrado em Computacao Cientifica")
        assert a == b
        assert hamming_distance(a, b) == 0

    def test_near_duplicate_small_distance(self) -> None:
        a = compute_simhash("Edital de Mestrado em Computacao Cientifica vagas 10")
        b = compute_simhash("Edital de Mestrado em Computacao Cientifica vagas 12")
        assert hamming_distance(a, b) <= 8

    def test_completely_different(self) -> None:
        a = compute_simhash("Mestrado em Geologia")
        b = compute_simhash("Doutorado em Linguistica de corpus")
        assert hamming_distance(a, b) > 8


class TestChangeDetector:
    def test_insert_when_no_prior(self) -> None:
        cd = ChangeDetector()
        assert cd.classify(None, 12345) is ChangeKind.INSERT

    def test_cosmetic_when_near(self) -> None:
        cd = ChangeDetector(near_threshold=3)
        prior = Edital(simhash=0b1111)
        # diferenca de 1 bit
        assert cd.classify(prior, 0b1110) is ChangeKind.COSMETIC

    def test_update_when_far(self) -> None:
        cd = ChangeDetector(near_threshold=3)
        prior = Edital(simhash=0b0)
        # diferenca de 10 bits
        assert cd.classify(prior, 0b1111111111) is ChangeKind.UPDATE
