"""Tabela de areas do conhecimento CNPq (subset relevante para o MVP).

Fonte: https://www.cnpq.br/documents/10157/186158/TabeladeAreasdoConhecimento.pdf

Decisao: nao carregamos a arvore completa (~9 grandes areas, ~76 areas, ~340 subareas).
Carregamos as relevantes ao perfil do usuario e expandimos sob demanda.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AreaCNPq:
    """Representa uma area do conhecimento CNPq pelo seu codigo numerico."""

    codigo: str        # ex: "10300007"
    nome: str          # ex: "Ciencia da Computacao"
    grande_area: str   # ex: "Ciencias Exatas e da Terra"

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nome}"


# ---------------------------------------------------------------------------
# Catalogo seed (expandido conforme novas areas aparecem em editais)
# ---------------------------------------------------------------------------
CATALOGO: dict[str, AreaCNPq] = {
    # Grande area: Ciencias Exatas e da Terra
    "10100002": AreaCNPq("10100002", "Matematica", "Ciencias Exatas e da Terra"),
    "10200006": AreaCNPq("10200006", "Probabilidade e Estatistica", "Ciencias Exatas e da Terra"),
    "10300007": AreaCNPq("10300007", "Ciencia da Computacao", "Ciencias Exatas e da Terra"),
    "10400000": AreaCNPq("10400000", "Astronomia", "Ciencias Exatas e da Terra"),
    "10500003": AreaCNPq("10500003", "Fisica", "Ciencias Exatas e da Terra"),
    "10600007": AreaCNPq("10600007", "Quimica", "Ciencias Exatas e da Terra"),
    "10700001": AreaCNPq("10700001", "Geociencias", "Ciencias Exatas e da Terra"),
    "10800005": AreaCNPq("10800005", "Oceanografia", "Ciencias Exatas e da Terra"),
    # Engenharias
    "30100007": AreaCNPq("30100007", "Engenharia Civil", "Engenharias"),
    "30200002": AreaCNPq("30200002", "Engenharia de Minas", "Engenharias"),
    "30300006": AreaCNPq("30300006", "Engenharia de Materiais e Metalurgica", "Engenharias"),
    "30400000": AreaCNPq("30400000", "Engenharia Eletrica", "Engenharias"),
    "30500004": AreaCNPq("30500004", "Engenharia Mecanica", "Engenharias"),
    "30700007": AreaCNPq("30700007", "Engenharia Quimica", "Engenharias"),
    "30900008": AreaCNPq("30900008", "Engenharia de Producao", "Engenharias"),
}


def get_by_codigo(codigo: str) -> AreaCNPq | None:
    return CATALOGO.get(codigo)


# Areas que aceitam bachareis em Ciencia da Computacao por afinidade (cross-discipline).
# Atualizado conforme aprendemos com editais reais.
ACEITAM_BACHAREIS_CC: frozenset[str] = frozenset(
    {
        "10300007",   # CC -> obvio
        "10100002",   # Matematica
        "10200006",   # Estatistica
        "10700001",   # Geociencias (geoinformatica, modelagem)
        "30400000",   # Eng. Eletrica (sistemas embarcados, sinais)
        "30900008",   # Eng. Producao (pesquisa operacional)
    }
)
