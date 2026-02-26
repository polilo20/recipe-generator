"""Scrapers package."""
from .aufilduthym import AufilduthymScraper
from .clemfoodie import ClemfoodieScraper
from .cestmafournee import CestmaFourneeScraper

AVAILABLE_SCRAPERS = {
    'aufilduthym': AufilduthymScraper,
    'clemfoodie': ClemfoodieScraper,
    'cestmafournee': CestmaFourneeScraper,
}
