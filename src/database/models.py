"""
Моделі бази даних для збереження даних конкурентної розвідки
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, 
    DateTime, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Competitor(Base):
    """Модель конкурента"""
    __tablename__ = 'competitors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(500), nullable=False)
    priority = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    seo_data = relationship("SEOData", back_populates="competitor", cascade="all, delete-orphan")
    company_data = relationship("CompanyData", back_populates="competitor", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="competitor", cascade="all, delete-orphan")
    promotions = relationship("Promotion", back_populates="competitor", cascade="all, delete-orphan")
    scan_history = relationship("ScanHistory", back_populates="competitor", cascade="all, delete-orphan")
    functional_tests = relationship("FunctionalTestResult", back_populates="competitor", cascade="all, delete-orphan") # NEW
    
    def __repr__(self):
        return f"<Competitor(name='{self.name}', url='{self.url}')>"


class ScanHistory(Base):
    """Історія сканувань"""
    __tablename__ = 'scan_history'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    scan_type = Column(String(50))  # full, seo, products, etc.
    status = Column(String(20))  # success, failed, partial
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    items_collected = Column(Integer, default=0)
    error_message = Column(Text)
    metadata_json = Column("metadata", JSON)
    
    competitor = relationship("Competitor", back_populates="scan_history")
    
    def __repr__(self):
        return f"<ScanHistory(competitor_id={self.competitor_id}, type='{self.scan_type}')>"


class SEOData(Base):
    """SEO дані сайту"""
    __tablename__ = 'seo_data'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    
    # Meta tags
    title = Column(String(500))
    meta_description = Column(Text)
    meta_keywords = Column(Text)
    meta_robots = Column(String(100))
    canonical_url = Column(String(500))
    
    # Open Graph
    og_title = Column(String(500))
    og_description = Column(Text)
    og_image = Column(String(500))
    og_type = Column(String(50))
    
    # Headings
    h1_tags = Column(JSON)  # List of H1 tags
    h2_tags = Column(JSON)  # List of H2 tags
    h3_tags = Column(JSON)  # List of H3 tags
    
    # Technical SEO
    robots_txt = Column(Text)
    sitemap_url = Column(String(500))
    sitemap_urls_count = Column(Integer)
    
    # Structured data
    structured_data = Column(JSON)  # JSON-LD, Schema.org
    
    # Links analysis
    internal_links_count = Column(Integer)
    external_links_count = Column(Integer)
    broken_links_count = Column(Integer)
    
    # Performance
    page_load_time = Column(Float)
    page_size_kb = Column(Integer)
    
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    competitor = relationship("Competitor", back_populates="seo_data")
    
    def __repr__(self):
        return f"<SEOData(competitor_id={self.competitor_id}, title='{self.title}')>"


class CompanyData(Base):
    """Контактні дані компанії"""
    __tablename__ = 'company_data'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    
    # Contact information
    emails = Column(JSON)  # List of emails
    phones = Column(JSON)  # List of phone numbers
    addresses = Column(JSON)  # List of addresses
    
    # Social media
    facebook_url = Column(String(500))
    instagram_url = Column(String(500))
    linkedin_url = Column(String(500))
    twitter_url = Column(String(500))
    youtube_url = Column(String(500))
    telegram_url = Column(String(500))
    
    # Business info
    company_name = Column(String(255))
    legal_name = Column(String(255))
    tax_id = Column(String(100))
    registration_number = Column(String(100))
    
    # Additional
    contact_forms = Column(JSON)  # List of contact form URLs
    support_chat = Column(Boolean, default=False)
    working_hours = Column(Text)
    
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    competitor = relationship("Competitor", back_populates="company_data")
    
    def __repr__(self):
        return f"<CompanyData(competitor_id={self.competitor_id})>"


class Product(Base):
    """Товар або послуга"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    
    # Basic info
    name = Column(String(500), nullable=False)
    sku = Column(String(100))
    url = Column(String(1000))
    category = Column(String(255))
    subcategory = Column(String(255))
    
    # Pricing
    price = Column(Float)
    currency = Column(String(10))
    old_price = Column(Float)  # Для знижок
    discount_percent = Column(Float)
    
    # Details
    description = Column(Text)
    short_description = Column(Text)
    specifications = Column(JSON)
    
    # Images
    main_image = Column(String(1000))
    images = Column(JSON)  # List of image URLs
    
    # Availability
    in_stock = Column(Boolean, default=True)
    stock_quantity = Column(Integer)
    available_for_order = Column(Boolean, default=True)
    
    # Ratings
    rating = Column(Float)
    reviews_count = Column(Integer)
    
    # Metadata
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    competitor = relationship("Competitor", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('competitor_id', 'url', name='uq_competitor_product_url'),
    )
    
    def __repr__(self):
        return f"<Product(name='{self.name}', price={self.price})>"


class PriceHistory(Base):
    """Історія змін цін"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    price = Column(Float, nullable=False)
    old_price = Column(Float)
    in_stock = Column(Boolean, default=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="price_history")
    
    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, price={self.price})>"


class Promotion(Base):
    """Акції та спеціальні пропозиції"""
    __tablename__ = 'promotions'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    
    # Basic info
    title = Column(String(500), nullable=False)
    description = Column(Text)
    url = Column(String(1000))
    
    # Promotion details
    promotion_type = Column(String(50))  # discount, sale, special_offer, coupon
    discount_value = Column(Float)
    discount_type = Column(String(20))  # percent, fixed, free_shipping
    promo_code = Column(String(100))
    
    # Terms
    terms_and_conditions = Column(Text)
    minimum_purchase = Column(Float)
    applicable_categories = Column(JSON)
    
    # Dates
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Image
    image_url = Column(String(1000))
    
    # Metadata
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    competitor = relationship("Competitor", back_populates="promotions")
    
    def __repr__(self):
        return f"<Promotion(title='{self.title}', type='{self.promotion_type}')>"


class LLMAnalysis(Base):
    """Результати аналізу LLM"""
    __tablename__ = 'llm_analysis'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'))
    analysis_type = Column(String(50))  # competitor_analysis, recommendations, etc.
    
    # Analysis results
    summary = Column(Text)
    strengths = Column(JSON)  # List of strengths
    weaknesses = Column(JSON)  # List of weaknesses
    opportunities = Column(JSON)  # List of opportunities
    threats = Column(JSON)  # List of threats
    recommendations = Column(JSON)  # List of recommendations
    
    # Full analysis
    full_analysis = Column(Text)
    
    # Metadata
    model_used = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time = Column(Float)
    
    def __repr__(self):
        return f"<LLMAnalysis(type='{self.analysis_type}', competitor_id={self.competitor_id})>"


class FunctionalTestResult(Base):
    """Результати функціонального тестування (реєстрація, форми)"""
    __tablename__ = 'functional_test_results'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    
    # Test results
    registration_status = Column(String(50)) # success, failed, skipped, error
    registration_message = Column(Text)
    contact_form_status = Column(String(50)) # success, failed, skipped, error
    contact_form_message = Column(Text)
    
    # Metadata
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    competitor = relationship("Competitor", back_populates="functional_tests")
    
    def __repr__(self):
        return f"<FunctionalTestResult(competitor_id={self.competitor_id}, reg_status='{self.registration_status}')>"
