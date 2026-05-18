from pos_editais_monitor.dedup.canonical_hash import canonical_hash
from pos_editais_monitor.dedup.change_detector import ChangeDetector, ChangeKind
from pos_editais_monitor.dedup.simhash import compute_simhash, hamming_distance

__all__ = [
    "ChangeDetector",
    "ChangeKind",
    "canonical_hash",
    "compute_simhash",
    "hamming_distance",
]
