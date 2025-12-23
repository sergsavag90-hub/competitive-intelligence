"""
Async-capable database manager with PostgreSQL primary/replica and Redis caching.
Provides a synchronous façade for existing callers while running async under the hood.
"""

import asyncio
import json
import logging
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import bcrypt
import asyncio

import redis.asyncio as aioredis
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload

from .models import (
    AuditLog,
    Base,
    CompanyData,
    Competitor,
    FunctionalTestResult,
    LLMAnalysis,
    PriceHistory,
    Product,
    Promotion,
    SEOData,
    ScanHistory,
    User,
)
from ..utils.config import config

logger = logging.getLogger(__name__)


def _get_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    if getattr(config, "database", None) and config.database.get("url"):
        return config.database["url"]
    return f"sqlite+aiosqlite:///{config.db_path}"


class AsyncDatabaseManager:
    """Base async manager that supports primary/replica connections."""

    def __init__(self, database_url: Optional[str] = None, replica_url: Optional[str] = None):
        self.database_url = database_url or _get_database_url()
        # Env templates may leave literal placeholders (e.g. "${DATABASE_REPLICA_URL:-}").
        # Treat those as "unset" so SQLAlchemy doesn't try to parse them.
        env_replica = replica_url or os.getenv("DATABASE_REPLICA_URL")
        self.replica_url = None if env_replica and env_replica.startswith("${") else env_replica
        self.engine: Optional[AsyncEngine] = None
        self.read_engine: Optional[AsyncEngine] = None
        self.Session: Optional[async_sessionmaker[AsyncSession]] = None
        self.ReadSession: Optional[async_sessionmaker[AsyncSession]] = None
        self.redis: Optional[aioredis.Redis] = None

    async def init(self) -> None:
        """Initialize engines, metadata, and Redis client."""
        self.engine = create_async_engine(
            self.database_url, pool_pre_ping=True, pool_size=20, max_overflow=50
        )
        self.read_engine = (
            create_async_engine(self.replica_url, pool_pre_ping=True, pool_size=20, max_overflow=50)
            if self.replica_url
            else self.engine
        )
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)
        self.ReadSession = async_sessionmaker(self.read_engine, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        redis_url = os.getenv("REDIS_URL") or (config.redis.get("url") if getattr(config, "redis", None) else None)
        if redis_url:
            self.redis = aioredis.from_url(redis_url, decode_responses=True)
            logger.info("Redis caching enabled at %s", redis_url)

    @asynccontextmanager
    async def session(self, read_only: bool = False) -> AsyncIterator[AsyncSession]:
        maker = self.ReadSession if read_only and self.ReadSession else self.Session
        if maker is None:
            raise RuntimeError("Database manager is not initialized.")
        async with maker() as session:
            try:
                yield session
            finally:
                await session.close()

    async def close(self) -> None:
        if self.engine:
            await self.engine.dispose()
        if self.read_engine and self.read_engine is not self.engine:
            await self.read_engine.dispose()
        if self.redis:
            await self.redis.close()

    # ---------- CRUD helpers ----------
    async def add_competitor(self, name: str, url: str, priority: int = 1, enabled: bool = True) -> Competitor:
        async with self.session() as session:
            competitor = Competitor(name=name, url=url, priority=priority, enabled=enabled)
            session.add(competitor)
            await session.commit()
            await session.refresh(competitor)
            return competitor

    async def get_competitor_by_name(self, name: str) -> Optional[Competitor]:
        async with self.session(read_only=True) as session:
            result = await session.execute(select(Competitor).where(Competitor.name == name))
            return result.scalar_one_or_none()

    async def get_competitor(self, competitor_id: int) -> Optional[Competitor]:
        cache_key = f"competitor:{competitor_id}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return self._deserialize_model(data, Competitor)

        async with self.session(read_only=True) as session:
            result = await session.execute(select(Competitor).where(Competitor.id == competitor_id))
            comp = result.scalar_one_or_none()
            if comp and self.redis:
                await self.redis.setex(cache_key, 300, json.dumps(self._serialize_model(comp), default=str))
            return comp

    async def get_all_competitors(self, enabled_only: bool = True) -> List[Competitor]:
        async with self.session(read_only=True) as session:
            stmt = select(Competitor)
            if enabled_only:
                stmt = stmt.where(Competitor.enabled.is_(True))
            stmt = stmt.order_by(Competitor.priority)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def start_scan(self, competitor_id: int, scan_type: str, metadata: Dict | None = None) -> ScanHistory:
        async with self.session() as session:
            scan = ScanHistory(
                competitor_id=competitor_id,
                scan_type=scan_type,
                status="running",
                metadata_json=metadata or {},
            )
            session.add(scan)
            await session.commit()
            await session.refresh(scan)
            return scan

    async def complete_scan(
        self, scan_id: int, status: str, items_collected: int = 0, error_message: str | None = None
    ) -> None:
        async with self.session() as session:
            scan = await session.get(ScanHistory, scan_id)
            if not scan:
                return
            scan.status = status
            scan.completed_at = datetime.utcnow()
            scan.items_collected = items_collected
            scan.error_message = error_message
            if scan.started_at:
                duration = (scan.completed_at - scan.started_at).total_seconds()
                scan.duration_seconds = int(duration)
            await session.commit()

    async def save_seo_data(self, competitor_id: int, seo_data: Dict[str, Any]) -> SEOData:
        async with self.session() as session:
            semantic_core = seo_data.pop("semantic_core", None)
            crawled_pages_count = seo_data.pop("crawled_pages_count", 0)
            seo = SEOData(
                competitor_id=competitor_id,
                semantic_core=semantic_core,
                crawled_pages_count=crawled_pages_count,
                **seo_data,
            )
            session.add(seo)
            await session.commit()
            await session.refresh(seo)

            if self.redis:
                key = f"seo:latest:{competitor_id}"
                await self.redis.set(key, json.dumps(self._serialize_model(seo)), ex=3600)
            return seo

    async def get_latest_seo_data(self, competitor_id: int) -> Optional[SEOData]:
        cache_key = f"seo:latest:{competitor_id}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                try:
                    return self._deserialize_model(json.loads(cached), SEOData)
                except Exception:
                    logger.exception("Failed to deserialize cached SEO data; falling back to DB.")
        async with self.session(read_only=True) as session:
            stmt = (
                select(SEOData)
                .where(SEOData.competitor_id == competitor_id)
                .order_by(SEOData.collected_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def save_company_data(self, competitor_id: int, company_data: Dict[str, Any]) -> CompanyData:
        async with self.session() as session:
            company = CompanyData(competitor_id=competitor_id, **company_data)
            session.add(company)
            await session.commit()
            await session.refresh(company)
            return company

    async def get_latest_company_data(self, competitor_id: int) -> Optional[CompanyData]:
        async with self.session(read_only=True) as session:
            stmt = (
                select(CompanyData)
                .where(CompanyData.competitor_id == competitor_id)
                .order_by(CompanyData.collected_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def add_or_update_product(self, competitor_id: int, product_data: Dict[str, Any]) -> Product:
        """
        Upsert product with optimistic locking and optional Redis distributed lock.
        Retries on IntegrityError with exponential backoff.
        """
        url = product_data.get("url")
        lock = None
        if self.redis and url:
            lock = self.redis.lock(f"product:{competitor_id}:{url}", timeout=10)
            await lock.acquire()

        try:
            backoff = [0.5, 1, 2]
            for attempt, delay in enumerate(backoff, start=1):
                try:
                    async with self.session() as session:
                        stmt = select(Product).where(
                            Product.competitor_id == competitor_id, Product.url == url
                        ).with_for_update()
                        result = await session.execute(stmt)
                        existing = result.scalar_one_or_none()

                        if existing:
                            for key, value in product_data.items():
                                if hasattr(existing, key):
                                    setattr(existing, key, value)
                            existing.last_seen = datetime.utcnow()

                            if "price" in product_data and product_data["price"] != existing.price:
                                price_history = PriceHistory(
                                    product_id=existing.id,
                                    price=product_data["price"],
                                    old_price=product_data.get("old_price"),
                                    in_stock=product_data.get("in_stock", True),
                                )
                                session.add(price_history)
                            product = existing
                        else:
                            product = Product(competitor_id=competitor_id, **product_data)
                            session.add(product)

                        await session.commit()
                        await session.refresh(product)

                        if self.redis and product.id:
                            await self._cache_price_history(session, product.id)
                        return product
                except IntegrityError as exc:
                    logger.warning("IntegrityError on product upsert (attempt %s): %s", attempt, exc)
                    if attempt >= len(backoff):
                        raise
                    await asyncio.sleep(delay)
        finally:
            if lock:
                try:
                    await lock.release()
                except Exception:
                    pass

    async def get_products(self, competitor_id: int, active_only: bool = True) -> List[Product]:
        async with self.session(read_only=True) as session:
            stmt = select(Product).where(Product.competitor_id == competitor_id)
            if active_only:
                stmt = stmt.where(Product.is_active.is_(True))
            result = await session.execute(stmt.options(selectinload(Product.price_history)))
            return list(result.scalars().all())

    async def get_price_history(self, product_id: int, days: int = 30) -> List[PriceHistory]:
        async with self.session(read_only=True) as session:
            cutoff = datetime.utcnow() - timedelta(days=max(days, 1))
            stmt = (
                select(PriceHistory)
                .where(PriceHistory.product_id == product_id)
                .where(PriceHistory.recorded_at >= cutoff)
                .order_by(PriceHistory.recorded_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_products_paginated(
        self,
        competitor_id: int,
        page: int = 1,
        size: int = 100,
        active_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Paginated fetch with optional Redis caching to reduce memory pressure on large datasets.
        """
        page = max(page, 1)
        size = max(1, min(size, 500))
        cache_key = f"products:{competitor_id}:{page}:{size}:{int(active_only)}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        async with self.session(read_only=True) as session:
            base_stmt = select(Product).where(Product.competitor_id == competitor_id)
            if active_only:
                base_stmt = base_stmt.where(Product.is_active.is_(True))

            total_stmt = select(func.count()).select_from(base_stmt.subquery())
            total_result = await session.execute(total_stmt)
            total = total_result.scalar_one()

            stmt = (
                base_stmt.order_by(Product.id)
                .offset((page - 1) * size)
                .limit(size)
                .options(selectinload(Product.price_history))
            )
            result = await session.execute(stmt)
            items = [self._serialize_model(prod) for prod in result.scalars().all()]

        payload = {"items": items, "page": page, "size": size, "total": total}
        if self.redis:
            await self.redis.setex(cache_key, 300, json.dumps(payload, default=str))
        return payload

    async def add_price_history(self, product_id: int, price: float, old_price: float | None = None) -> PriceHistory:
        async with self.session() as session:
            history = PriceHistory(product_id=product_id, price=price, old_price=old_price)
            session.add(history)
            await session.commit()
            await session.refresh(history)
            if self.redis:
                await self._cache_price_history(session, product_id)
            return history

    async def _cache_price_history(self, session: AsyncSession, product_id: int) -> None:
        stmt = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.recorded_at.desc())
            .limit(20)
        )
        result = await session.execute(stmt)
        history = [self._serialize_model(h) for h in result.scalars().all()]
        pipe = self.redis.pipeline()
        pipe.set(f"price_history:{product_id}", json.dumps(history), ex=3600)
        await pipe.execute()

    async def save_promotion(self, competitor_id: int, promo_data: Dict[str, Any]) -> Promotion:
        async with self.session() as session:
            promo = Promotion(competitor_id=competitor_id, **promo_data)
            session.add(promo)
            await session.commit()
            await session.refresh(promo)
            return promo

    async def save_llm_analysis(self, competitor_id: int, analysis: Dict[str, Any]) -> LLMAnalysis:
        async with self.session() as session:
            record = LLMAnalysis(competitor_id=competitor_id, **analysis)
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def save_functional_test(self, competitor_id: int, result: Dict[str, Any]) -> FunctionalTestResult:
        async with self.session() as session:
            record = FunctionalTestResult(competitor_id=competitor_id, **result)
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def save_functional_test_data(self, competitor_id: int, result: Dict[str, Any]) -> FunctionalTestResult:
        return await self.save_functional_test(competitor_id, result)

    async def add_or_update_promotion(self, competitor_id: int, promo_data: Dict[str, Any]) -> Promotion:
        async with self.session() as session:
            stmt = select(Promotion).where(
                Promotion.competitor_id == competitor_id, Promotion.url == promo_data.get("url")
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                for key, value in promo_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                promo = existing
            else:
                promo = Promotion(competitor_id=competitor_id, **promo_data)
                session.add(promo)
            await session.commit()
            await session.refresh(promo)
            return promo

    async def get_active_promotions(self, competitor_id: int) -> List[Promotion]:
        async with self.session(read_only=True) as session:
            stmt = select(Promotion).where(
                Promotion.competitor_id == competitor_id, Promotion.is_active.is_(True)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_competitor_stats(self, competitor_id: int) -> Dict[str, Any]:
        async with self.session(read_only=True) as session:
            stats: Dict[str, Any] = {}
            result = await session.execute(
                select(ScanHistory)
                .where(ScanHistory.competitor_id == competitor_id)
                .order_by(ScanHistory.completed_at.desc())
                .limit(1)
            )
            stats["last_scan"] = result.scalar_one_or_none()
            result = await session.execute(
                select(Product).where(Product.competitor_id == competitor_id, Product.is_active.is_(True))
            )
            stats["total_products"] = len(result.scalars().all())
            result = await session.execute(
                select(Promotion).where(Promotion.competitor_id == competitor_id, Promotion.is_active.is_(True))
            )
            stats["total_promotions"] = len(result.scalars().all())
            stats["has_seo_data"] = (
                await session.execute(
                    select(SEOData).where(SEOData.competitor_id == competitor_id).limit(1)
                )
            ).scalar_one_or_none() is not None
            stats["has_company_data"] = (
                await session.execute(
                    select(CompanyData).where(CompanyData.competitor_id == competitor_id).limit(1)
                )
            ).scalar_one_or_none() is not None
            return stats

    # ---------- Auth helpers ----------
    def _hash_password(self, password: str) -> str:
        rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")

    def _check_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    def _hash_api_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    async def create_user(self, email: str, password: str, role: str = "viewer") -> User:
        async with self.session() as session:
            user = User(email=email, password_hash=self._hash_password(password), role=role)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        async with self.session(read_only=True) as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        async with self.session(read_only=True) as session:
            return await session.get(User, user_id)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        # lock check
        if user.lock_until and user.lock_until > datetime.utcnow():
            return None
        if not self._check_password(password, user.password_hash):
            await self._increment_failed_attempts(user.id)
            return None
        await self._reset_failed_attempts(user.id)
        return user

    async def _increment_failed_attempts(self, user_id: str) -> None:
        lock_window = timedelta(minutes=15)
        async with self.session() as session:
            user = await session.get(User, user_id)
            if not user:
                return
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= 5:
                user.lock_until = datetime.utcnow() + lock_window
                user.failed_attempts = 0
            await session.commit()

    async def _reset_failed_attempts(self, user_id: str) -> None:
        async with self.session() as session:
            user = await session.get(User, user_id)
            if not user:
                return
            user.failed_attempts = 0
            user.lock_until = None
            await session.commit()

    async def generate_api_key(self, user_id: str) -> str:
        api_key = secrets.token_hex(32)
        api_hash = self._hash_api_key(api_key)
        async with self.session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise ValueError("User not found")
            user.api_key_hash = api_hash
            await session.commit()
        return api_key

    async def revoke_api_key(self, user_id: str) -> None:
        async with self.session() as session:
            user = await session.get(User, user_id)
            if not user:
                return
            user.api_key_hash = None
            await session.commit()

    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        api_hash = self._hash_api_key(api_key)
        async with self.session(read_only=True) as session:
            result = await session.execute(select(User).where(User.api_key_hash == api_hash))
            return result.scalar_one_or_none()

    async def log_audit(
        self,
        user_id: Optional[str],
        action: str,
        resource: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        async with self.session() as session:
            record = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {},
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def update_password(self, user_id: str, new_password: str) -> None:
        async with self.session() as session:
            user = await session.get(User, user_id)
            if not user:
                return
            user.password_hash = self._hash_password(new_password)
            await session.commit()

    # ---------- Migration helpers ----------
    async def migrate_from_sqlite(self, sqlite_path: str) -> None:
        """Migrate data from a SQLite file into the current database."""
        sqlite_url = f"sqlite+aiosqlite:///{sqlite_path}"
        sqlite_engine = create_async_engine(sqlite_url)
        sqlite_session = async_sessionmaker(sqlite_engine, expire_on_commit=False)

        async with sqlite_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sqlite_session() as s_src, self.session() as s_dst:
            for model in (Competitor, ScanHistory, SEOData, CompanyData, Product, PriceHistory, Promotion, LLMAnalysis, FunctionalTestResult):
                result = await s_src.execute(select(model))
                rows = result.scalars().all()
                batch = []
                for row in rows:
                    data = self._serialize_model(row)
                    batch.append(model(**data))
                s_dst.add_all(batch)
                await s_dst.commit()

        await sqlite_engine.dispose()
        logger.info("Migration from SQLite %s completed", sqlite_path)

    # ---------- Serialization helpers ----------
    def _serialize_model(self, obj: Any) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for column in obj.__table__.columns:
            data[column.name] = getattr(obj, column.name)
        return data

    def _deserialize_model(self, payload: Dict[str, Any], model_cls):
        return model_cls(**payload)


class SQLiteDatabaseManager(AsyncDatabaseManager):
    """Lightweight fallback using SQLite for testing."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(database_url=f"sqlite+aiosqlite:///{self.db_path}")


class PostgresDatabaseManager(AsyncDatabaseManager):
    """PostgreSQL primary/replica manager with Redis caching."""

    def __init__(self):
        database_url = os.getenv("DATABASE_URL") or config.get("database.url")
        replica_url = os.getenv("DATABASE_REPLICA_URL") or config.get("database.replica_url")
        super().__init__(database_url=database_url, replica_url=replica_url)


class DatabaseManager:
    """
    Backward-compatible façade exposing sync-style methods while using async managers under the hood.
    """

    def __init__(self):
        use_postgres = (config.get("database.type") == "postgres") or os.getenv("DATABASE_URL", "").startswith(
            "postgresql"
        )
        if use_postgres:
            self.backend: AsyncDatabaseManager = PostgresDatabaseManager()
        else:
            self.backend = SQLiteDatabaseManager()
        self._loop = None
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If we're inside an active event loop (e.g., uvicorn/uvloop), schedule init asynchronously.
            loop.create_task(self.backend.init())
            self._loop = loop
            return

        self._loop = loop
        self._loop.run_until_complete(self.backend.init())

    def _run(self, coro):
        """
        Execute an async coroutine from sync context.

        - If there's a running loop (uvicorn), schedule thread-safe and wait for result.
        - Otherwise, drive the coroutine on the current loop.
        """
        loop = self._loop or asyncio.get_event_loop()
        self._loop = loop
        if loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        return loop.run_until_complete(coro)

    # Synchronous wrappers
    def add_competitor(self, *args, **kwargs):
        return self._run(self.backend.add_competitor(*args, **kwargs))

    def get_competitor_by_name(self, *args, **kwargs):
        return self._run(self.backend.get_competitor_by_name(*args, **kwargs))

    def get_competitor(self, *args, **kwargs):
        return self._run(self.backend.get_competitor(*args, **kwargs))

    def get_all_competitors(self, *args, **kwargs):
        return self._run(self.backend.get_all_competitors(*args, **kwargs))

    def start_scan(self, *args, **kwargs):
        return self._run(self.backend.start_scan(*args, **kwargs))

    def complete_scan(self, *args, **kwargs):
        return self._run(self.backend.complete_scan(*args, **kwargs))

    def save_seo_data(self, *args, **kwargs):
        return self._run(self.backend.save_seo_data(*args, **kwargs))

    def get_latest_seo_data(self, *args, **kwargs):
        return self._run(self.backend.get_latest_seo_data(*args, **kwargs))

    def save_company_data(self, *args, **kwargs):
        return self._run(self.backend.save_company_data(*args, **kwargs))

    def get_latest_company_data(self, *args, **kwargs):
        return self._run(self.backend.get_latest_company_data(*args, **kwargs))

    def add_or_update_product(self, *args, **kwargs):
        return self._run(self.backend.add_or_update_product(*args, **kwargs))

    def get_products(self, *args, **kwargs):
        return self._run(self.backend.get_products(*args, **kwargs))

    def get_price_history(self, *args, **kwargs):
        return self._run(self.backend.get_price_history(*args, **kwargs))

    def get_products_paginated(self, *args, **kwargs):
        return self._run(self.backend.get_products_paginated(*args, **kwargs))

    def add_price_history(self, *args, **kwargs):
        return self._run(self.backend.add_price_history(*args, **kwargs))

    def save_promotion(self, *args, **kwargs):
        return self._run(self.backend.save_promotion(*args, **kwargs))

    def add_or_update_promotion(self, *args, **kwargs):
        return self._run(self.backend.add_or_update_promotion(*args, **kwargs))

    def save_llm_analysis(self, *args, **kwargs):
        return self._run(self.backend.save_llm_analysis(*args, **kwargs))

    def save_functional_test(self, *args, **kwargs):
        return self._run(self.backend.save_functional_test(*args, **kwargs))

    def save_functional_test_data(self, *args, **kwargs):
        return self._run(self.backend.save_functional_test_data(*args, **kwargs))

    def migrate_from_sqlite(self, sqlite_path: str):
        return self._run(self.backend.migrate_from_sqlite(sqlite_path))

    def get_active_promotions(self, *args, **kwargs):
        return self._run(self.backend.get_active_promotions(*args, **kwargs))

    def get_competitor_stats(self, *args, **kwargs):
        return self._run(self.backend.get_competitor_stats(*args, **kwargs))

    # Auth wrappers
    def create_user(self, *args, **kwargs):
        return self._run(self.backend.create_user(*args, **kwargs))

    def get_user_by_email(self, *args, **kwargs):
        return self._run(self.backend.get_user_by_email(*args, **kwargs))

    def authenticate_user(self, *args, **kwargs):
        return self._run(self.backend.authenticate_user(*args, **kwargs))

    def generate_api_key(self, *args, **kwargs):
        return self._run(self.backend.generate_api_key(*args, **kwargs))

    def revoke_api_key(self, *args, **kwargs):
        return self._run(self.backend.revoke_api_key(*args, **kwargs))

    def get_user_by_api_key(self, *args, **kwargs):
        return self._run(self.backend.get_user_by_api_key(*args, **kwargs))

    def log_audit(self, *args, **kwargs):
        return self._run(self.backend.log_audit(*args, **kwargs))

    def get_user_by_id(self, *args, **kwargs):
        return self._run(self.backend.get_user_by_id(*args, **kwargs))

    def update_password(self, *args, **kwargs):
        return self._run(self.backend.update_password(*args, **kwargs))
