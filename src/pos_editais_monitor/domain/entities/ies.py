from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from pos_editais_monitor.core.utils import utcnow


@dataclass(slots=True)
class IES:
    """Instituicao de Ensino Superior, espelho do cadastro e-MEC.

    Apenas IES com `ativa=True` e `gratuita=True` passam pelo gate da pipeline.
    """

    id: UUID = field(default_factory=uuid4)
    codigo_emec: str = ""              # ex: "0521"
    sigla: str = ""                    # ex: "UFRGS"
    nome: str = ""                     # ex: "Universidade Federal do Rio Grande do Sul"
    categoria_administrativa: str = "" # "Publica Federal", "Especial", "Publica Estadual", etc.
    organizacao_academica: str = ""    # "Universidade", "Instituto Federal", etc.
    uf: str = ""
    municipio: str = ""
    ativa: bool = True                 # situacao_cadastral == ATIVA
    gratuita: bool = True              # nao cobra mensalidade
    atualizado_em: datetime = field(default_factory=utcnow)

    @property
    def elegivel(self) -> bool:
        """Passa pelo gate da pipeline?"""
        return self.ativa and self.gratuita
