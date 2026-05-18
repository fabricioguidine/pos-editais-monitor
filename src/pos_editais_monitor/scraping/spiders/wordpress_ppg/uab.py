from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class UABSpider(PPGWordPressSpider):
    """UAB - Universidade Aberta do Brasil (via eduCAPES).

    UAB nao tem portal centralizado com RSS confiavel. educapes hospeda
    listagens. Best-effort.
    """

    name = "uab"
    ies_nome = "Universidade Aberta do Brasil"
    feed_url = None
    listing_url = "https://educapes.capes.gov.br/"
