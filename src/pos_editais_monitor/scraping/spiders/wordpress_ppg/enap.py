from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class ENAPSpider(PPGWordPressSpider):
    """ENAP - Escola Nacional de Administracao Publica.

    Oferece MBA e especializacao em gestao publica gratuitos.
    robots.txt permissivo (Allow: /). Sem RSS direto - vai via listing.
    """

    name = "enap"
    ies_nome = "Escola Nacional de Administracao Publica"
    feed_url = None
    listing_url = "https://www.enap.gov.br/"
