"""Scrapers package"""

from .seo_scraper import SEOScraper
from .company_scraper import CompanyScraper
from .product_scraper import ProductScraper
from .promotion_scraper import PromotionScraper
from .functional_test_scraper import FunctionalTestScraper

__all__ = [
    "SEOScraper",
    "CompanyScraper",
    "ProductScraper",
    "PromotionScraper",
    "FunctionalTestScraper",
]
