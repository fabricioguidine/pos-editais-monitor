"""Detecta se um ParsedEdital recem-chegado e:

- INSERT: nao existe em DB (canonical_hash novo)
- COSMETIC: existe, simhash quase identico (<=3 bits) -> nao notifica
- UPDATE: existe, simhash divergiu materialmente -> notifica re-envio
"""

from __future__ import annotations

from enum import Enum

from pos_editais_monitor.dedup.simhash import hamming_distance
from pos_editais_monitor.domain.entities.edital import Edital


class ChangeKind(Enum):
    INSERT = "insert"
    COSMETIC = "cosmetic"
    UPDATE = "update"


class ChangeDetector:
    def __init__(self, near_threshold: int = 3) -> None:
        self._near = near_threshold

    def classify(self, existing: Edital | None, new_simhash: int) -> ChangeKind:
        if existing is None:
            return ChangeKind.INSERT
        distance = hamming_distance(existing.simhash, new_simhash)
        if distance <= self._near:
            return ChangeKind.COSMETIC
        return ChangeKind.UPDATE
