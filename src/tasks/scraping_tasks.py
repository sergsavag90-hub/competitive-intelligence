import logging
import json
import os
import traceback
from datetime import datetime
from redis import Redis

from src.celery_app import celery_app
from src.scrapers.company_scraper import CompanyScraper
from src.scrapers.product_scraper import ProductScraper
from src.scrapers.seo_scraper import SEOScraper
from src.scrapers.promotion_scraper import PromotionScraper

logger = logging.getLogger(__name__)
redis_url = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
dlq = Redis.from_url(redis_url) if redis_url else None


def send_to_dlq(payload: dict) -> None:
    if not dlq:
        logger.error("DLQ not configured; payload=%s", payload)
        return
    try:
        dlq.lpush("dlq:tasks", json.dumps(payload))
    except Exception as exc:
        logger.error("Failed to push to DLQ: %s", exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    name="tasks.scrape_competitor_task",
    acks_late=True,
    reject_on_worker_lost=True,
    queue="high-priority",
)
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
        send_to_dlq(
            {
                "task_id": self.request.id,
                "competitor_id": competitor_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

# Reliability tuning
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1
