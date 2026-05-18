from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class UnicampIMESpider(PPGWordPressSpider):
    name = "unicamp-ime"
    ies_nome = "Universidade Estadual de Campinas"
    feed_url = "https://www.ime.unicamp.br/feed/"
    listing_url = "https://www.ime.unicamp.br/pos-graduacao"
