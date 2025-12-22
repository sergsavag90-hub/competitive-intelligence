from __future__ import annotations

from typing import Dict, List

from src.database.db_manager import DatabaseManager

db = DatabaseManager()


def get_products(competitor_id: int | None = None, page: int = 1, size: int = 100) -> Dict:
    """
    Fetch paginated products; if competitor_id is None returns empty payload to avoid heavy full-table scans.
    """
    if competitor_id is None:
        return {"items": [], "page": 1, "size": 0, "total": 0}
    return db.get_products_paginated(competitor_id, page=page, size=size)


def get_price_history(product_id: int, days: int = 30):
    return db.get_price_history(product_id, days=days)
