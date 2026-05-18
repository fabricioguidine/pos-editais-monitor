from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from pos_editais_monitor.core.utils import utcnow
from pos_editais_monitor.domain.enums.fonte_tipo import FonteTipo


@dataclass(slots=True)
class Fonte:
    """Fonte de monitoramento (ex.: 'capes', 'ufrgs-ppg', 'sigaa-ufrn')."""

    id: UUID = field(default_factory=uuid4)
    codigo: str = ""           # slug curto, unico
    nome: str = ""             # nome humano
    tipo: FonteTipo = FonteTipo.OUTRO
    base_url: str = ""
    ativa: bool = True
    intervalo_minutos: int = 180
    spider_class: str = ""     # path completo da classe Python do spider
    criada_em: datetime = field(default_factory=utcnow)
    ultima_execucao: datetime | None = None
    ultima_execucao_status: str | None = None
