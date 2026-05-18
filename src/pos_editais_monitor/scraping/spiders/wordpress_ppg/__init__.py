from pos_editais_monitor.scraping.spiders.wordpress_ppg.base import PPGWordPressSpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.enap import ENAPSpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.ifrs import IFRSSpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.ifsp import IFSPSpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.uab import UABSpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.ufmg_dcc import UFMGDCCSpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.ufrgs_inf import UFRGSInfSpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.unicamp_ime import UnicampIMESpider
from pos_editais_monitor.scraping.spiders.wordpress_ppg.usp_ime import USPIMESpider

__all__ = [
    "ENAPSpider",
    "IFRSSpider",
    "IFSPSpider",
    "PPGWordPressSpider",
    "UABSpider",
    "UFMGDCCSpider",
    "UFRGSInfSpider",
    "USPIMESpider",
    "UnicampIMESpider",
]
