from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    version: str
    components: dict[str, str] = Field(default_factory=dict)
