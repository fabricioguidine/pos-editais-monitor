from __future__ import annotations

from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider


class IFRSSpider(PPGWordPressSpider):
    """IFRS - Instituto Federal do Rio Grande do Sul.

    RSS feed publico e robots.txt permissivo. Publica muita especializacao
    lato sensu presencial e EAD.
    """

    name = "ifrs"
    ies_nome = "Instituto Federal de Educacao, Ciencia e Tecnologia do Rio Grande do Sul"
    feed_url = "https://ifrs.edu.br/feed/"
    listing_url = "https://ifrs.edu.br/noticias/"
