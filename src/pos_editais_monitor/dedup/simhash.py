"""Simhash 64-bit para deteccao de quase-duplicatas."""

from __future__ import annotations

import re

from simhash import Simhash

from pos_editais_monitor.parsers.fields.normalize import normalize_to_ascii

_TOKEN_RE = re.compile(r"\w+")


def compute_simhash(text: str) -> int:
    """64-bit simhash de tokens normalizados (ASCII lowercase)."""
    tokens = _TOKEN_RE.findall(normalize_to_ascii(text))
    if not tokens:
        return 0
    return Simhash(tokens).value


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
