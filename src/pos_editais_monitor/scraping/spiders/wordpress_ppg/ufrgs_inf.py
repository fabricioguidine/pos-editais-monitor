from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class UFRGSInfSpider(PPGWordPressSpider):
    name = "ufrgs-inf"
    ies_nome = "Universidade Federal do Rio Grande do Sul"
    feed_url = "https://www.inf.ufrgs.br/site/feed/"
    listing_url = "https://www.inf.ufrgs.br/site/pos-graduacao/"
