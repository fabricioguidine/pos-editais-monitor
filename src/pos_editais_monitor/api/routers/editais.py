from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.api.dependencies import db_session
from pos_editais_monitor.api.schemas.common import Page
from pos_editais_monitor.api.schemas.edital import EditalRead
from pos_editais_monitor.infrastructure.db.models.edital import EditalModel

router = APIRouter(prefix="/v1/editais", tags=["editais"])


@router.get("", response_model=Page[EditalRead], summary="Lista paginada de editais")
async def list_editais(
    session: Annotated[AsyncSession, Depends(db_session)],
    nivel: Annotated[str | None, Query()] = None,
    modalidade: Annotated[str | None, Query()] = None,
    area: Annotated[str | None, Query()] = None,
    apenas_abertos: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[EditalRead]:
    stmt = select(EditalModel)
    if nivel:
        stmt = stmt.where(EditalModel.nivel == nivel)
    if modalidade:
        stmt = stmt.where(EditalModel.modalidade == modalidade)
    if area:
        stmt = stmt.where(EditalModel.area_cnpq_codigo == area)
    if apenas_abertos:
        from datetime import date
        today = date.today()
        stmt = stmt.where(
            (EditalModel.inscricao_ate.is_(None)) | (EditalModel.inscricao_ate >= today)
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()
    rows = (
        await session.execute(stmt.order_by(EditalModel.inscricao_ate.asc().nullslast()).limit(limit).offset(offset))
    ).scalars().all()
    items = [EditalRead.from_entity(m.to_entity()) for m in rows]
    return Page[EditalRead](items=items, total=total, limit=limit, offset=offset)


@router.get("/{edital_id}", response_model=EditalRead)
async def get_edital(
    edital_id: str,
    session: Annotated[AsyncSession, Depends(db_session)],
) -> EditalRead:
    from uuid import UUID
    try:
        oid = UUID(edital_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid id") from exc
    m = await session.get(EditalModel, oid)
    if not m:
        raise HTTPException(status_code=404, detail="not found")
    return EditalRead.from_entity(m.to_entity())
