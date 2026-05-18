"""Hash canonico de edital: sha256 sobre campos normalizados."""

from __future__ import annotations

import hashlib

from pos_editais_monitor.domain.entities.edital import ParsedEdital
from pos_editais_monitor.parsers.fields.normalize import normalize_to_ascii


def canonical_hash(p: ParsedEdital) -> str:
    """Composicao deterministica de campos eliminatorios.

    Mudar a definicao aqui INVALIDA os hashes antigos -> requer migration de
    re-hash. Versionar (`canonical_hash_v1`) quando for o caso.
    """
    parts = [
        normalize_to_ascii(p.titulo),
        normalize_to_ascii(p.ies_nome),
        p.nivel.value,
        p.modalidade.value,
        (p.periodo_inscricao.isoformat() if p.periodo_inscricao else ""),
        p.fonte_codigo,
    ]
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
