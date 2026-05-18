"""Cliente Anthropic Claude — fallback de parsing.

Decisoes:
- Usa `claude-haiku-4-5` (rapido, barato, suficiente para extracao estruturada).
- Prompt caching ativo no system prompt (5min TTL).
- Resposta esperada eh JSON estrito; falha de parse vai para dead-letter.
- Logs estruturados com tokens in/out + cached.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, TextBlockParam

from pos_editais_monitor.core.config import Settings, get_settings
from pos_editais_monitor.core.logging import get_logger
from pos_editais_monitor.core.observability import METRICS

log = get_logger(__name__)

SYSTEM_PROMPT_EDITAL = (
    "Voce eh um extrator de campos estruturados de editais de pos-graduacao "
    "brasileiros. Dada uma string com o texto do edital (HTML simplificado ou "
    "texto de PDF), retorne JSON ESTRITO no formato:\n\n"
    "{\n"
    '  "titulo": str,\n'
    '  "nivel": "especializacao|mba|mestrado_academico|mestrado_profissional|doutorado|desconhecido",\n'
    '  "modalidade": "presencial|ead|semipresencial|uab|desconhecida",\n'
    '  "ies_nome": str,\n'
    '  "area_concentracao": str | null,\n'
    '  "vagas": int | null,\n'
    '  "is_gratuito": bool | null,\n'
    '  "periodo_inscricao": {"de": "YYYY-MM-DD" | null, "ate": "YYYY-MM-DD" | null},\n'
    '  "identificador_externo": str | null,\n'
    '  "link_pdf": str | null,\n'
    '  "confidence": float (0..1)\n'
    "}\n\n"
    "Regras:\n"
    "- Retorne APENAS o JSON, sem markdown, sem explicacao.\n"
    "- Se um campo nao for inferivel, use null (ou 'desconhecido' para enums).\n"
    "- 'confidence' eh sua estimativa de quao bom foi o seu proprio parsing.\n"
    "- Datas em portugues ('30 de junho de 2026') devem ser convertidas para ISO.\n"
)


class AnthropicLLMClient:
    """Wrapper sobre AsyncAnthropic com instrumentacao."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = AsyncAnthropic(
            api_key=self._settings.anthropic_api_key.get_secret_value(),
        )

    async def extrair_edital(self, texto: str) -> dict[str, Any] | None:
        """Extrai campos do edital. Retorna dict validavel por Pydantic ou None
        se a chamada falhar / JSON for invalido."""
        if not self._settings.llm_enabled:
            return None
        truncado = texto[:6000]
        system: list[TextBlockParam] = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT_EDITAL,
                "cache_control": {"type": "ephemeral"},   # prompt cache 5min
            },
        ]
        messages: list[MessageParam] = [
            {
                "role": "user",
                "content": (
                    "Extraia o JSON estrito do edital abaixo. Texto:\n\n<<<\n"
                    f"{truncado}\n>>>"
                ),
            }
        ]
        try:
            resp = await self._client.messages.create(
                model=self._settings.llm_model,
                max_tokens=self._settings.llm_max_tokens,
                system=system,
                messages=messages,
            )
        except Exception as exc:  # rede / quota / auth
            log.warning("llm_call_failed", err=str(exc))
            METRICS.llm_fallback_invocations_total.labels("error").inc()
            return None

        # Telemetria de tokens
        usage = resp.usage
        METRICS.llm_tokens_total.labels("input").inc(usage.input_tokens)
        METRICS.llm_tokens_total.labels("output").inc(usage.output_tokens)
        if hasattr(usage, "cache_read_input_tokens"):
            METRICS.llm_tokens_total.labels("cached").inc(
                usage.cache_read_input_tokens or 0
            )
        METRICS.llm_fallback_invocations_total.labels("ok").inc()

        # Esperamos um unico TextBlock como resposta
        if not resp.content:
            log.warning("llm_empty_response")
            return None
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            log.warning("llm_invalid_json", err=str(exc), text=text[:300])
            METRICS.llm_fallback_invocations_total.labels("invalid_json").inc()
            return None
        return data
