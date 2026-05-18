"""Object store para snapshots brutos (HTML/PDF).

MVP: filesystem local em `./storage/snapshots/...`.
v0.3: implementacao S3/MinIO mantendo a mesma interface `ObjectStore`.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    """Interface ports-and-adapters. Pipeline depende disto, nao da implementacao."""

    async def put(self, prefix: str, body: bytes, suffix: str) -> tuple[str, str]:
        """Persiste o body. Retorna (storage_path, sha256)."""

    async def get(self, storage_path: str) -> bytes:
        """Le bytes do path. Levanta FileNotFoundError se ausente."""


class LocalObjectStore:
    def __init__(self, base_dir: str | Path = "storage/snapshots") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    async def put(self, prefix: str, body: bytes, suffix: str) -> tuple[str, str]:
        sha = hashlib.sha256(body).hexdigest()
        today = date.today().isoformat()
        rel = Path(prefix) / today / f"{sha}{suffix}"
        full = self._base / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        if not full.exists():
            full.write_bytes(body)
        return str(rel).replace("\\", "/"), sha

    async def get(self, storage_path: str) -> bytes:
        full = self._base / storage_path
        return full.read_bytes()
