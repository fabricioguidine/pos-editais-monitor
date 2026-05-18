"""Spiders: estrategias concretas por fonte. Registry abaixo.

DOU e Sucupira ficam no codigo mas FORA do registry ativo - ambos respondem
robots.txt 'Disallow: /'. Para uso futuro com flag opt-in.
"""

from pos_editais_monitor.scraping.spiders.base.spider import BaseSpider
from pos_editais_monitor.scraping.spiders.dou.dou_spider import DouSpider  # noqa: F401
from pos_editais_monitor.scraping.spiders.sucupira.sucupira_spider import (  # noqa: F401
    SucupiraSpider,
)
from pos_editais_monitor.scraping.spiders.wordpress_ppg import (
    ENAPSpider,
    IFRSSpider,
    IFSPSpider,
    UABSpider,
    UFMGDCCSpider,
    UFRGSInfSpider,
    UnicampIMESpider,
    USPIMESpider,
)

SPIDER_REGISTRY: dict[str, type[BaseSpider]] = {
    # Foco em especializacao/MBA gratuitos
    "ifrs": IFRSSpider,
    "ifsp": IFSPSpider,
    "enap": ENAPSpider,
    "uab": UABSpider,
    # Mestrados/doutorados (off pra perfil atual, mas spiders ativos)
    "ufrgs-inf": UFRGSInfSpider,
    "usp-ime": USPIMESpider,
    "ufmg-dcc": UFMGDCCSpider,
    "unicamp-ime": UnicampIMESpider,
}

__all__ = [
    "ENAPSpider",
    "IFRSSpider",
    "IFSPSpider",
    "SPIDER_REGISTRY",
    "BaseSpider",
    "UABSpider",
    "UFMGDCCSpider",
    "UFRGSInfSpider",
    "USPIMESpider",
    "UnicampIMESpider",
]
