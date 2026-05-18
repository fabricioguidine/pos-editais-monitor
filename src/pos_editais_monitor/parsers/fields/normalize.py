"""Normalizacao de texto para parsing e dedup."""

from __future__ import annotations

import re
import unicodedata

from unidecode import unidecode

_WHITESPACE_RE = re.compile(r"\s+")
_INVISIBLE_RE = re.compile(r"[​‌‍﻿]")


def normalize_text(text: str) -> str:
    """NFKC + colapsa whitespace + remove zero-width chars."""
    t = unicodedata.normalize("NFKC", text or "")
    t = _INVISIBLE_RE.sub("", t)
    t = _WHITESPACE_RE.sub(" ", t).strip()
    return t


def normalize_to_ascii(text: str) -> str:
    """Para hash canonico e matching: ASCII lower."""
    return unidecode(normalize_text(text)).lower()
