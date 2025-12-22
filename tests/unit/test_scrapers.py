import pytest
from selenium.common.exceptions import TimeoutException

from src.scrapers.seo_scraper import SEOScraper


def test_seo_scraper_handles_timeout(mock_selenium_driver):
    scraper = SEOScraper()
    mock_selenium_driver.get.side_effect = TimeoutException()
    with pytest.raises(Exception):
        scraper.process_url(mock_selenium_driver, "https://example.com")
