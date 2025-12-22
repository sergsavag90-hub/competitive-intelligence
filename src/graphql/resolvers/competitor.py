from __future__ import annotations

import logging
from typing import List, Optional

from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

db = DatabaseManager()


def get_competitor_by_id(competitor_id: int):
    return db.get_competitor(competitor_id)


def list_competitors(enabled_only: bool = True):
    return db.get_all_competitors(enabled_only=enabled_only)


def get_products_for_competitor(competitor_id: int, page: int = 1, size: int = 100):
    return db.get_products_paginated(competitor_id, page=page, size=size)


def trigger_scan_job(competitor_id: int) -> str:
    """
    Placeholder for triggering a scan; in production this could enqueue Celery task.
    """
    logger.info("GraphQL triggerScan for competitor %s (stub enqueue)", competitor_id)
    return "queued"
