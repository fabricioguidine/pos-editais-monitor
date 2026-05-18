from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class IFSPSpider(PPGWordPressSpider):
    """IFSP - Instituto Federal de Sao Paulo.

    robots.txt 403 (nao existe = permitido). Listagem de processos
    seletivos em URL dedicada.
    """

    name = "ifsp"
    ies_nome = "Instituto Federal de Educacao, Ciencia e Tecnologia de Sao Paulo"
    feed_url = None
    listing_url = "https://www.ifsp.edu.br/processos-seletivos"
