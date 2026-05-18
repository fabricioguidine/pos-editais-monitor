from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class USPIMESpider(PPGWordPressSpider):
    name = "usp-ime"
    ies_nome = "Universidade de Sao Paulo"
    feed_url = "https://www.ime.usp.br/feed/"
    listing_url = "https://www.ime.usp.br/posgraduacao/"
