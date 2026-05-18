from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class UFMGDCCSpider(PPGWordPressSpider):
    name = "ufmg-dcc"
    ies_nome = "Universidade Federal de Minas Gerais"
    feed_url = None  # nao tem RSS; usa listagem
    listing_url = "https://www.ppgcc.dcc.ufmg.br/"
