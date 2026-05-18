from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from pos_editais_monitor.core.utils import utcnow


@dataclass(slots=True)
class Snapshot:
    """Instantaneo bruto de uma pagina/PDF de edital.

    Sempre persistido para auditoria e replay. O `storage_path` aponta para
    arquivo em `infrastructure/storage` (filesystem local no MVP, S3-compat depois).
    """

    id: UUID = field(default_factory=uuid4)
    edital_id: UUID | None = None
    fonte_id: UUID | None = None
    url: str = ""
    http_status: int = 0
    content_type: str = ""           # "text/html", "application/pdf"
    sha256: str = ""
    bytes_size: int = 0
    storage_path: str = ""           # ex.: "capes/2026-05-10/abc123.html"
    capturado_em: datetime = field(default_factory=utcnow)
    parser_name: str | None = None
    parse_confidence: float | None = None
    headers: dict[str, str] = field(default_factory=dict)
