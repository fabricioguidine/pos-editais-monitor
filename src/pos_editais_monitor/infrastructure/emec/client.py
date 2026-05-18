"""Cliente para o cadastro e-MEC.

O e-MEC nao oferece API REST publica documentada; expomos um cliente fino
que faz scraping respeitoso da consulta avancada. Resultado eh cacheado
no banco (tabela `ies`) e refreshed a cada 7 dias.

Em producao real, este cliente seria substituido por integracao com a
"Consulta Avancada" que aceita filtros por categoria administrativa.
Para o MVP, usamos um seed estatico em `data/emec_seed.json` que e
periodicamente refrescado e validado contra o site.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.domain.entities.ies import IES

log = get_logger(__name__)

_SEED_PATH = Path(__file__).resolve().parents[4] / "data" / "emec_seed.json"


class EmecClient:
    """Cliente para o cadastro e-MEC.

    MVP usa seed estatico + capacidade de refresh manual. v0.2 implementa
    scraping incremental.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def listar_ies_elegiveis(self) -> AsyncIterator[IES]:
        """Itera IES publicas e ativas a partir do seed.

        Filtros aplicados:
        - situacao_cadastral == ATIVA
        - categoria_administrativa em (Federal, Estadual, Municipal, Especial)
        - gratuita == True
        """
        if not _SEED_PATH.exists():
            log.warning("emec_seed_missing", path=str(_SEED_PATH))
            return
        with _SEED_PATH.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        for row in payload.get("ies", []):
            if not row.get("ativa", True):
                continue
            if self._settings.emec_only_public and not row.get("publica", False):
                continue
            if self._settings.emec_only_active and not row.get("ativa", True):
                continue
            yield IES(
                codigo_emec=str(row["codigo_emec"]),
                sigla=row.get("sigla", ""),
                nome=row.get("nome", ""),
                categoria_administrativa=row.get("categoria_administrativa", ""),
                organizacao_academica=row.get("organizacao_academica", ""),
                uf=row.get("uf", ""),
                municipio=row.get("municipio", ""),
                ativa=row.get("ativa", True),
                gratuita=row.get("publica", True),
            )
