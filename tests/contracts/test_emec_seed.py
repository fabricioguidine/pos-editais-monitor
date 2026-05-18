"""Contract test: o seed local do e-MEC continua produzindo IES elegiveis?"""

import json
from pathlib import Path

import pytest

_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "emec_seed.json"


@pytest.mark.contract
def test_seed_is_valid_json_and_has_ies() -> None:
    assert _SEED_PATH.exists(), f"seed missing at {_SEED_PATH}"
    payload = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    ies = payload.get("ies", [])
    assert len(ies) >= 10, "expected at least 10 seed IES"
    required_keys = {"codigo_emec", "sigla", "nome", "categoria_administrativa", "ativa", "publica"}
    for row in ies:
        missing = required_keys - set(row.keys())
        assert not missing, f"missing keys {missing} in {row.get('sigla')}"
