"""Extracao de datas em portugues brasileiro.

Padroes comuns:
- 'de 01/03/2026 a 15/04/2026'
- 'das 09:00 do dia 01/03/2026 ate 17:00 de 15/04/2026'
- '01 de marco a 15 de abril de 2026'
- 'ate 30 de junho de 2026' (apenas data fim)
- 'inscricoes ate 30/06/2026'

Implementacao determinista com regex (sem dateparser para evitar ambiguidade).
"""

from __future__ import annotations

import re
from datetime import date

from pos_editais_monitor.domain.value_objects.periodo import PeriodoInscricao

_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

# 01/03/2026  ou  1/3/2026
_DDMMYYYY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
# 01 de marco de 2026  ou  1 de marco 2026
_BR_LONG = re.compile(
    r"\b(\d{1,2})\s+de\s+([a-zçãáéíóú]+)(?:\s+de)?\s+(\d{4})\b",
    re.IGNORECASE,
)


def _parse_ddmmyyyy(m: re.Match[str]) -> date | None:
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _parse_br_long(m: re.Match[str]) -> date | None:
    d = int(m.group(1))
    mes_txt = m.group(2).lower()
    y = int(m.group(3))
    mo = _MESES.get(mes_txt)
    if mo is None:
        return None
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _find_all_dates(text: str) -> list[date]:
    """Retorna todas as datas validas encontradas, na ordem de aparicao."""
    out: list[tuple[int, date]] = []
    for m in _DDMMYYYY.finditer(text):
        d = _parse_ddmmyyyy(m)
        if d:
            out.append((m.start(), d))
    for m in _BR_LONG.finditer(text):
        d = _parse_br_long(m)
        if d:
            out.append((m.start(), d))
    out.sort(key=lambda t: t[0])
    return [d for _, d in out]


def extract_periodo_inscricao(text: str) -> PeriodoInscricao | None:
    """Heuristica:
    1. Procura janela 'inscric*' / 'periodo de inscricao' / 'das ... ate ...'.
    2. Captura as 2 primeiras datas dentro de ~200 chars dessa janela.
    3. Se so 1 data e o contexto for 'ate'/'prazo' -> (None, data).
    """
    if not text:
        return None
    lower = text.lower()
    # Janela proximo a palavra-chave
    keys = ("inscric", "prazo", "periodo de inscri", "submissao")
    window: str | None = None
    for k in keys:
        i = lower.find(k)
        if i >= 0:
            window = text[max(0, i - 20) : i + 300]
            break
    if window is None:
        window = text[:600]

    datas = _find_all_dates(window)
    if not datas:
        return None
    if len(datas) == 1:
        # Heuristica: se 'ate' aparece antes da data, eh data fim
        win_lower = window.lower()
        if "ate" in win_lower or "limite" in win_lower or "prazo" in win_lower:
            return PeriodoInscricao(de=None, ate=datas[0])
        return PeriodoInscricao(de=datas[0], ate=None)
    return PeriodoInscricao(de=datas[0], ate=datas[1])
