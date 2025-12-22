import logging

from src.celery_app import celery_app
from src.scrapers.company_scraper import CompanyScraper
from src.scrapers.product_scraper import ProductScraper
from src.scrapers.seo_scraper import SEOScraper
from src.scrapers.promotion_scraper import PromotionScraper

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=2, name="tasks.scrape_competitor_task")
def scrape_competitor_task(self, competitor_id: int, modules=None):
    """High-priority scrape task with exponential backoff."""
    modules = modules or ["seo", "company", "products", "promotions"]
    try:
        result = {}
        if "seo" in modules:
            scraper = SEOScraper()
            result["seo"] = scraper.run_for_competitor(competitor_id)
        if "company" in modules:
            scraper = CompanyScraper()
            result["company"] = scraper.run_for_competitor(competitor_id)
        if "products" in modules:
            scraper = ProductScraper()
            result["products"] = scraper.run_for_competitor(competitor_id)
        if "promotions" in modules:
            scraper = PromotionScraper()
            result["promotions"] = scraper.run_for_competitor(competitor_id)
        return {"status": "success", "data": result}
    except Exception as exc:
        logger.error("Task %s failed for competitor %s", self.request.id, competitor_id, exc_info=True)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

# Reliability tuning
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1
