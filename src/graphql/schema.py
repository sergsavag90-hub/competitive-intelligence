from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import strawberry
from strawberry import federation

from src.database.models import Product as ProductModel, Competitor as CompetitorModel, PriceHistory as PriceHistoryModel, SEOData
from src.graphql.resolvers import competitor as competitor_resolvers
from src.graphql.resolvers import product as product_resolvers

logger = logging.getLogger(__name__)


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


@strawberry.type
class PriceHistory:
    id: int
    price: float
    old_price: Optional[float]
    in_stock: bool
    recorded_at: Optional[str]

    @staticmethod
    def from_model(model: PriceHistoryModel) -> "PriceHistory":
        return PriceHistory(
            id=model.id,
            price=model.price,
            old_price=model.old_price,
            in_stock=model.in_stock,
            recorded_at=_dt(model.recorded_at),
        )


@strawberry.type
class Product:
    id: int
    name: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    url: Optional[str]
    category: Optional[str]
    in_stock: Optional[bool]
    main_image: Optional[str]
    last_seen: Optional[str]
    price_history: List[PriceHistory]

    @staticmethod
    def from_model(model: ProductModel) -> "Product":
        return Product(
            id=model.id,
            name=model.name,
            price=model.price,
            currency=model.currency,
            url=model.url,
            category=model.category,
            in_stock=model.in_stock,
            main_image=model.main_image,
            last_seen=_dt(model.last_seen),
            price_history=[PriceHistory.from_model(h) for h in getattr(model, "price_history", [])],
        )


@strawberry.type
class SEOMetrics:
    title: Optional[str]
    meta_description: Optional[str]
    canonical_url: Optional[str]
    page_load_time: Optional[float]
    crawled_pages_count: Optional[int]
    collected_at: Optional[str]

    @staticmethod
    def from_model(model: SEOData | None) -> Optional["SEOMetrics"]:
        if not model:
            return None
        return SEOMetrics(
            title=model.title,
            meta_description=model.meta_description,
            canonical_url=model.canonical_url,
            page_load_time=model.page_load_time,
            crawled_pages_count=model.crawled_pages_count,
            collected_at=_dt(model.collected_at),
        )


@strawberry.type
class Competitor:
    id: int
    name: str
    url: str
    priority: int
    enabled: bool


@strawberry.type
class ProductsPage:
    items: List[Product]
    page: int
    size: int
    total: int


@strawberry.type
class ScanJob:
    status: str
    job_id: str


@strawberry.type
class Query:
    @strawberry.field
    def competitor(self, id: strawberry.ID) -> Optional[Competitor]:
        comp = competitor_resolvers.get_competitor_by_id(int(id))
        if not comp:
            return None
        return Competitor(
            id=comp.id,
            name=comp.name,
            url=comp.url,
            priority=comp.priority,
            enabled=comp.enabled,
        )

    @strawberry.field
    def products(self, competitor_id: int, page: int = 1, size: int = 100) -> ProductsPage:
        payload = product_resolvers.get_products(competitor_id=competitor_id, page=page, size=size)
        items = [Product.from_model(ProductModel(**item)) if isinstance(item, dict) else Product.from_model(item) for item in payload.get("items", [])]
        return ProductsPage(items=items, page=payload.get("page", 1), size=payload.get("size", 0), total=payload.get("total", 0))

    @strawberry.field
    def price_trends(self, product_id: int, days: int = 30) -> List[PriceHistory]:
        history = product_resolvers.get_price_history(product_id, days=days)
        return [PriceHistory.from_model(h) for h in history]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def trigger_scan(self, competitor_id: int) -> ScanJob:
        job_id = competitor_resolvers.trigger_scan_job(competitor_id)
        return ScanJob(status="queued", job_id=str(job_id))

    @strawberry.mutation
    def create_alert(self, rule: str) -> bool:
        logger.info("Received alert rule via GraphQL: %s", rule)
        return True


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def price_changes(self, product_id: int) -> PriceHistory:
        """
        Basic demo subscription: polls price history and yields the latest snapshot periodically.
        """
        last_id = None
        while True:
            history = await asyncio.to_thread(product_resolvers.get_price_history, product_id, 1)
            if history:
                latest = history[0]
                if latest.id != last_id:
                    last_id = latest.id
                    yield PriceHistory.from_model(latest)
            await asyncio.sleep(5)


schema = federation.Schema(query=Query, mutation=Mutation, subscription=Subscription)
