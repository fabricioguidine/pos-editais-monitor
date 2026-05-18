"""Whitelist de IES — gate da pipeline.

Carrega o conjunto de siglas/nomes normalizados das IES elegiveis e responde
em O(1) se uma string de IES vinda de spider pertence ao conjunto.
"""

from __future__ import annotations

from unidecode import unidecode

from pos_editais_monitor.domain.entities.ies import IES


def _norm(s: str) -> str:
    return unidecode(s).lower().strip()


class EmecWhitelist:
    """Aceita strings vindas de spiders e responde se a IES eh elegivel.

    Constroi um set de siglas + nomes + tokens significativos do nome
    para tolerar variacoes ('UFRGS' vs 'Universidade Federal do Rio Grande do Sul').
    """

    def __init__(self, ies_list: list[IES]) -> None:
        self._by_codigo: dict[str, IES] = {i.codigo_emec: i for i in ies_list}
        self._by_token: dict[str, IES] = {}
        for ies in ies_list:
            if not ies.elegivel:
                continue
            for tok in self._tokens(ies):
                self._by_token[tok] = ies

    @staticmethod
    def _tokens(ies: IES) -> list[str]:
        toks = []
        if ies.sigla:
            toks.append(_norm(ies.sigla))
        if ies.nome:
            toks.append(_norm(ies.nome))
        return toks

    def lookup(self, ies_string: str) -> IES | None:
        n = _norm(ies_string)
        direct = self._by_token.get(n)
        if direct:
            return direct
        # busca por substring (frase mais longa)
        for tok, ies in self._by_token.items():
            if tok and tok in n:
                return ies
        return None

    def contains(self, ies_string: str) -> bool:
        return self.lookup(ies_string) is not None

    @property
    def size(self) -> int:
        return len(self._by_codigo)
