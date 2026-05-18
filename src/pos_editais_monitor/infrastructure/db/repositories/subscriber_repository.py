from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pos_editais_monitor.domain.entities.subscriber import (
    AreaAlvo,
    MatchMode,
    SubscriberProfile,
)
from pos_editais_monitor.domain.enums.modalidade import Modalidade
from pos_editais_monitor.domain.enums.nivel import Nivel
from pos_editais_monitor.infrastructure.db.models.subscriber import SubscriberModel


class SubscriberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_nome(self, nome: str) -> SubscriberProfile | None:
        stmt = select(SubscriberModel).where(SubscriberModel.nome == nome)
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_profile(m) if m else None

    async def list_ativos(self) -> list[SubscriberProfile]:
        stmt = select(SubscriberModel).where(SubscriberModel.ativo.is_(True))
        return [_to_profile(m) for m in (await self._session.execute(stmt)).scalars().all()]

    async def upsert(self, p: SubscriberProfile) -> SubscriberProfile:
        existing = await self.get_by_nome(p.nome)
        payload = _profile_to_json(p)
        if existing:
            stmt = select(SubscriberModel).where(SubscriberModel.nome == p.nome)
            m = (await self._session.execute(stmt)).scalar_one()
            m.email = p.email
            m.formacao = p.formacao
            m.profile_json = payload
            m.score_minimo = p.score_minimo
            m.digest_cron = p.digest_cron
            m.ativo = p.ativo
            return _to_profile(m)
        m = SubscriberModel(
            id=p.id,
            nome=p.nome,
            email=p.email,
            formacao=p.formacao,
            profile_json=payload,
            score_minimo=p.score_minimo,
            digest_cron=p.digest_cron,
            ativo=p.ativo,
        )
        self._session.add(m)
        await self._session.flush()
        return _to_profile(m)


def _profile_to_json(p: SubscriberProfile) -> dict:
    return {
        "areas_alvo": [
            {
                "codigo_cnpq": a.codigo_cnpq,
                "modo": a.modo.value,
                "peso": a.peso,
                "requer_aceita_cs": a.requer_aceita_cs,
            }
            for a in p.areas_alvo
        ],
        "niveis_aceitos": [n.value for n in p.niveis_aceitos],
        "modalidades_aceitas": [m.value for m in p.modalidades_aceitas],
        "apenas_gratuitos": p.apenas_gratuitos,
        "apenas_ies_emec_publicas": p.apenas_ies_emec_publicas,
    }


def _to_profile(m: SubscriberModel) -> SubscriberProfile:
    payload = m.profile_json
    if isinstance(payload, str):
        payload = json.loads(payload)
    areas = [
        AreaAlvo(
            codigo_cnpq=a["codigo_cnpq"],
            modo=MatchMode(a["modo"]),
            peso=float(a["peso"]),
            requer_aceita_cs=bool(a.get("requer_aceita_cs", False)),
        )
        for a in payload.get("areas_alvo", [])
    ]
    return SubscriberProfile(
        id=m.id,
        nome=m.nome,
        email=m.email,
        formacao=m.formacao,
        areas_alvo=areas,
        niveis_aceitos={Nivel(x) for x in payload.get("niveis_aceitos", [])},
        modalidades_aceitas={Modalidade(x) for x in payload.get("modalidades_aceitas", [])},
        apenas_gratuitos=bool(payload.get("apenas_gratuitos", True)),
        apenas_ies_emec_publicas=bool(payload.get("apenas_ies_emec_publicas", True)),
        score_minimo=m.score_minimo,
        digest_cron=m.digest_cron,
        ativo=m.ativo,
    )
