"""
Async SQLAlchemy models with optional field-level encryption.
"""

import json
import os
import logging
from datetime import datetime
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        # Fallback key only for development; real deployments must set FERNET_KEY
        key = Fernet.generate_key()
        logger.warning("FERNET_KEY not set; generated ephemeral key for encryption.")
    try:
        return Fernet(key)
    except Exception as exc:  # pragma: no cover
        logger.error("Invalid FERNET_KEY provided: %s", exc)
        return Fernet(Fernet.generate_key())


_fernet = _get_fernet()


class EncryptedText(TypeDecorator):
    """Encrypts text values at rest using Fernet."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[bytes]:
        if value is None:
            return None
        token = _fernet.encrypt(value.encode("utf-8"))
        return token

    def process_result_value(self, value: Optional[bytes], dialect) -> Optional[str]:
        if value is None:
            return None
        try:
            return _fernet.decrypt(value).decode("utf-8")
        except InvalidToken:
            logger.error("Failed to decrypt text field; returning None.")
            return None


class EncryptedJSON(TypeDecorator):
    """Encrypts JSON-compatible objects at rest."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> Optional[bytes]:
        if value is None:
            return None
        payload = json.dumps(value).encode("utf-8")
        return _fernet.encrypt(payload)

    def process_result_value(self, value: Optional[bytes], dialect) -> Any:
        if value is None:
            return None
        try:
            decrypted = _fernet.decrypt(value).decode("utf-8")
            return json.loads(decrypted)
        except InvalidToken:
            logger.error("Failed to decrypt JSON field; returning None.")
            return None


class Base(DeclarativeBase):
    pass


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    seo_data: Mapped[list["SEOData"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    company_data: Mapped[list["CompanyData"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    promotions: Mapped[list["Promotion"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    scan_history: Mapped[list["ScanHistory"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    functional_tests: Mapped[list["FunctionalTestResult"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )


class ScanHistory(Base):
    __tablename__ = "scan_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False)
    scan_type: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[Optional[str]] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    items_collected: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    competitor: Mapped[Competitor] = relationship(back_populates="scan_history")


class SEOData(Base):
    __tablename__ = "seo_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    meta_description: Mapped[Optional[str]] = mapped_column(Text)
    meta_keywords: Mapped[Optional[str]] = mapped_column(Text)
    meta_robots: Mapped[Optional[str]] = mapped_column(String(100))
    canonical_url: Mapped[Optional[str]] = mapped_column(String(500))
    og_title: Mapped[Optional[str]] = mapped_column(String(500))
    og_description: Mapped[Optional[str]] = mapped_column(Text)
    og_image: Mapped[Optional[str]] = mapped_column(String(500))
    og_type: Mapped[Optional[str]] = mapped_column(String(50))
    h1_tags: Mapped[Optional[list[str]]] = mapped_column(JSON)
    h2_tags: Mapped[Optional[list[str]]] = mapped_column(JSON)
    h3_tags: Mapped[Optional[list[str]]] = mapped_column(JSON)
    robots_txt: Mapped[Optional[str]] = mapped_column(Text)
    sitemap_url: Mapped[Optional[str]] = mapped_column(String(500))
    sitemap_urls_count: Mapped[Optional[int]] = mapped_column(Integer)
    structured_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    internal_links_count: Mapped[Optional[int]] = mapped_column(Integer)
    external_links_count: Mapped[Optional[int]] = mapped_column(Integer)
    broken_links_count: Mapped[Optional[int]] = mapped_column(Integer)
    page_load_time: Mapped[Optional[float]] = mapped_column(Float)
    page_size_kb: Mapped[Optional[int]] = mapped_column(Integer)
    crawled_pages_count: Mapped[int] = mapped_column(Integer, default=0)
    semantic_core: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    competitor: Mapped[Competitor] = relationship(back_populates="seo_data")


class CompanyData(Base):
    __tablename__ = "company_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False)
    emails: Mapped[Optional[list[str]]] = mapped_column(EncryptedJSON)
    phones: Mapped[Optional[list[str]]] = mapped_column(EncryptedJSON)
    addresses: Mapped[Optional[list[str]]] = mapped_column(EncryptedJSON)
    facebook_url: Mapped[Optional[str]] = mapped_column(String(500))
    instagram_url: Mapped[Optional[str]] = mapped_column(String(500))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    twitter_url: Mapped[Optional[str]] = mapped_column(String(500))
    youtube_url: Mapped[Optional[str]] = mapped_column(String(500))
    telegram_url: Mapped[Optional[str]] = mapped_column(String(500))
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    legal_name: Mapped[Optional[str]] = mapped_column(String(255))
    tax_id: Mapped[Optional[str]] = mapped_column(String(100))
    registration_number: Mapped[Optional[str]] = mapped_column(String(100))
    contact_forms: Mapped[Optional[list[str]]] = mapped_column(JSON)
    support_chat: Mapped[bool] = mapped_column(Boolean, default=False)
    working_hours: Mapped[Optional[str]] = mapped_column(Text)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    competitor: Mapped[Competitor] = relationship(back_populates="company_data")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("competitor_id", "url", name="uq_competitor_product_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(100))
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    category: Mapped[Optional[str]] = mapped_column(String(255))
    subcategory: Mapped[Optional[str]] = mapped_column(String(255))
    price: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    old_price: Mapped[Optional[float]] = mapped_column(Float)
    discount_percent: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    short_description: Mapped[Optional[str]] = mapped_column(Text)
    specifications: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    main_image: Mapped[Optional[str]] = mapped_column(String(1000))
    images: Mapped[Optional[list[str]]] = mapped_column(JSON)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    available_for_order: Mapped[bool] = mapped_column(Boolean, default=True)
    rating: Mapped[Optional[float]] = mapped_column(Float)
    reviews_count: Mapped[Optional[int]] = mapped_column(Integer)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    competitor: Mapped[Competitor] = relationship(back_populates="products")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    old_price: Mapped[Optional[float]] = mapped_column(Float)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="price_history")


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    promotion_type: Mapped[Optional[str]] = mapped_column(String(50))
    discount_value: Mapped[Optional[float]] = mapped_column(Float)
    discount_type: Mapped[Optional[str]] = mapped_column(String(20))
    promo_code: Mapped[Optional[str]] = mapped_column(String(100))
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text)
    minimum_purchase: Mapped[Optional[float]] = mapped_column(Float)
    applicable_categories: Mapped[Optional[list[str]]] = mapped_column(JSON)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000))
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    competitor: Mapped[Competitor] = relationship(back_populates="promotions")


class LLMAnalysis(Base):
    __tablename__ = "llm_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitors.id"))
    analysis_type: Mapped[Optional[str]] = mapped_column(String(50))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    strengths: Mapped[Optional[list[str]]] = mapped_column(JSON)
    weaknesses: Mapped[Optional[list[str]]] = mapped_column(JSON)
    opportunities: Mapped[Optional[list[str]]] = mapped_column(JSON)
    threats: Mapped[Optional[list[str]]] = mapped_column(JSON)
    recommendations: Mapped[Optional[list[str]]] = mapped_column(JSON)
    full_analysis: Mapped[Optional[str]] = mapped_column(Text)
    model_used: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processing_time: Mapped[Optional[float]] = mapped_column(Float)


class FunctionalTestResult(Base):
    __tablename__ = "functional_test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False)
    registration_status: Mapped[Optional[str]] = mapped_column(String(50))
    registration_message: Mapped[Optional[str]] = mapped_column(Text)
    contact_form_status: Mapped[Optional[str]] = mapped_column(String(50))
    contact_form_message: Mapped[Optional[str]] = mapped_column(Text)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    competitor: Mapped[Competitor] = relationship(back_populates="functional_tests")


# Import auth/audit models so metadata is aware
from .user import User  # noqa: E402,F401
from .audit import AuditLog  # noqa: E402,F401
