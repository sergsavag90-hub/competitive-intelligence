"""
Менеджер бази даних для управління збереженням та отриманням даних
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, Competitor, SEOData, CompanyData, Product, 
    Promotion, ScanHistory, PriceHistory, LLMAnalysis, FunctionalTestResult
)
from ..utils.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Клас для управління базою даних"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.db_path
        self.engine = None
        self.Session = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Ініціалізація бази даних"""
        # Створюємо папку для БД якщо не існує
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Створюємо engine
        db_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(db_url, echo=False)
        
        # Створюємо таблиці
        Base.metadata.create_all(self.engine)
        
        # Створюємо session factory
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info(f"База даних ініціалізована: {self.db_path}")
    
    def get_session(self) -> Session:
        """Отримати нову сесію"""
        return self.Session()
    
    # ==================== COMPETITOR ====================
    
    def add_competitor(self, name: str, url: str, priority: int = 1, enabled: bool = True) -> Competitor:
        """Додати конкурента"""
        session = self.get_session()
        try:
            competitor = Competitor(
                name=name,
                url=url,
                priority=priority,
                enabled=enabled
            )
            session.add(competitor)
            session.commit()
            session.refresh(competitor)
            logger.info(f"Додано конкурента: {name}")
            return competitor
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Помилка додавання конкурента: {e}")
            raise
        finally:
            session.close()
    
    def get_competitor_by_name(self, name: str) -> Optional[Competitor]:
        """Отримати конкурента за іменем"""
        session = self.get_session()
        try:
            return session.query(Competitor).filter_by(name=name).first()
        finally:
            session.close()
    
    def get_all_competitors(self, enabled_only: bool = True) -> List[Competitor]:
        """Отримати всіх конкурентів"""
        session = self.get_session()
        try:
            query = session.query(Competitor)
            if enabled_only:
                query = query.filter_by(enabled=True)
            return query.order_by(Competitor.priority).all()
        finally:
            session.close()
    
    # ==================== SCAN HISTORY ====================
    
    def start_scan(self, competitor_id: int, scan_type: str, metadata: Dict = None) -> ScanHistory:
        """Почати сканування"""
        session = self.get_session()
        try:
            scan = ScanHistory(
                competitor_id=competitor_id,
                scan_type=scan_type,
                status='running',
                metadata_json=metadata or {}
            )
            session.add(scan)
            session.commit()
            session.refresh(scan)
            return scan
        finally:
            session.close()
    
    def complete_scan(self, scan_id: int, status: str, items_collected: int = 0, 
                     error_message: str = None):
        """Завершити сканування"""
        session = self.get_session()
        try:
            scan = session.query(ScanHistory).get(scan_id)
            if scan:
                scan.status = status
                scan.completed_at = datetime.utcnow()
                scan.items_collected = items_collected
                scan.error_message = error_message
                
                if scan.started_at:
                    duration = (scan.completed_at - scan.started_at).total_seconds()
                    scan.duration_seconds = int(duration)
                
                session.commit()
        finally:
            session.close()
    
    # ==================== SEO DATA ====================
    
    def save_seo_data(self, competitor_id: int, seo_data: Dict[str, Any]) -> SEOData:
        """Зберегти SEO дані"""
        session = self.get_session()
        try:
            # Витягуємо нові поля, які не є частиною моделі SEOData
            semantic_core = seo_data.pop('semantic_core', None)
            crawled_pages_count = seo_data.pop('crawled_pages_count', 0)
            
            seo = SEOData(
                competitor_id=competitor_id, 
                semantic_core=semantic_core,
                crawled_pages_count=crawled_pages_count,
                **seo_data
            )
            session.add(seo)
            session.commit()
            session.refresh(seo)
            logger.info(f"Збережено SEO дані для competitor_id={competitor_id}")
            return seo
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Помилка збереження SEO даних: {e}")
            raise
        finally:
            session.close()
    
    def get_latest_seo_data(self, competitor_id: int) -> Optional[SEOData]:
        """Отримати останні SEO дані"""
        session = self.get_session()
        try:
            return session.query(SEOData)\
                .filter_by(competitor_id=competitor_id)\
                .order_by(SEOData.collected_at.desc())\
                .first()
        finally:
            session.close()
    
    # ==================== COMPANY DATA ====================
    
    def save_company_data(self, competitor_id: int, company_data: Dict[str, Any]) -> CompanyData:
        """Зберегти дані компанії"""
        session = self.get_session()
        try:
            company = CompanyData(competitor_id=competitor_id, **company_data)
            session.add(company)
            session.commit()
            session.refresh(company)
            logger.info(f"Збережено дані компанії для competitor_id={competitor_id}")
            return company
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Помилка збереження даних компанії: {e}")
            raise
        finally:
            session.close()
    
    def get_latest_company_data(self, competitor_id: int) -> Optional[CompanyData]:
        """Отримати останні дані компанії"""
        session = self.get_session()
        try:
            return session.query(CompanyData)\
                .filter_by(competitor_id=competitor_id)\
                .order_by(CompanyData.collected_at.desc())\
                .first()
        finally:
            session.close()
    
    # ==================== PRODUCTS ====================
    
    def add_or_update_product(self, competitor_id: int, product_data: Dict[str, Any]) -> Product:
        """Додати або оновити товар"""
        session = self.get_session()
        try:
            # Шукаємо існуючий продукт
            existing = session.query(Product).filter(
                and_(
                    Product.competitor_id == competitor_id,
                    Product.url == product_data.get('url')
                )
            ).first()
            
            if existing:
                # Оновлюємо існуючий
                for key, value in product_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_seen = datetime.utcnow()
                
                # Додаємо історію цін якщо ціна змінилась
                if 'price' in product_data and product_data['price'] != existing.price:
                    price_history = PriceHistory(
                        product_id=existing.id,
                        price=product_data['price'],
                        old_price=product_data.get('old_price'),
                        in_stock=product_data.get('in_stock', True)
                    )
                    session.add(price_history)
                
                product = existing
            else:
                # Створюємо новий
                product = Product(competitor_id=competitor_id, **product_data)
                session.add(product)
            
            session.commit()
            session.refresh(product)
            return product
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Помилка збереження товару: {e}")
            raise
        finally:
            session.close()
    
    def get_products(self, competitor_id: int, active_only: bool = True) -> List[Product]:
        """Отримати товари конкурента"""
        session = self.get_session()
        try:
            query = session.query(Product).filter_by(competitor_id=competitor_id)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.all()
        finally:
            session.close()
    
    # ==================== PROMOTIONS ====================
    
    def add_or_update_promotion(self, competitor_id: int, promo_data: Dict[str, Any]) -> Promotion:
        """Додати або оновити акцію"""
        session = self.get_session()
        try:
            # Шукаємо існуючу акцію за URL або заголовком
            existing = None
            if promo_data.get('url'):
                existing = session.query(Promotion).filter(
                    and_(
                        Promotion.competitor_id == competitor_id,
                        Promotion.url == promo_data['url']
                    )
                ).first()
            
            if existing:
                for key, value in promo_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_seen = datetime.utcnow()
                promotion = existing
            else:
                promotion = Promotion(competitor_id=competitor_id, **promo_data)
                session.add(promotion)
            
            session.commit()
            session.refresh(promotion)
            return promotion
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Помилка збереження акції: {e}")
            raise
        finally:
            session.close()
    
    def get_active_promotions(self, competitor_id: Optional[int] = None) -> List[Promotion]:
        """Отримати активні акції"""
        session = self.get_session()
        try:
            query = session.query(Promotion).filter_by(is_active=True)
            if competitor_id:
                query = query.filter_by(competitor_id=competitor_id)
            return query.order_by(Promotion.start_date.desc()).all()
        finally:
            session.close()
    
    # ==================== FUNCTIONAL TEST ====================
    
    def save_functional_test_data(self, competitor_id: int, test_data: Dict[str, Any]) -> 'FunctionalTestResult':
        """Зберегти результати функціонального тестування"""
        session = self.get_session()
        try:
            # Extract data from the nested structure
            reg_data = test_data.get('registration_test', {})
            contact_data = test_data.get('contact_form_test', {})
            
            test_result = FunctionalTestResult(
                competitor_id=competitor_id,
                registration_status=reg_data.get('status', 'error'),
                registration_message=reg_data.get('message', 'No message'),
                contact_form_status=contact_data.get('status', 'error'),
                contact_form_message=contact_data.get('message', 'No message')
            )
            session.add(test_result)
            session.commit()
            session.refresh(test_result)
            logger.info(f"Збережено результати функціонального тестування для competitor_id={competitor_id}")
            return test_result
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Помилка збереження результатів функціонального тестування: {e}")
            raise
        finally:
            session.close()

    # ==================== LLM ANALYSIS ====================
    
    def save_llm_analysis(self, analysis_data: Dict[str, Any]) -> LLMAnalysis:
        """Зберегти результати LLM аналізу"""
        session = self.get_session()
        try:
            analysis = LLMAnalysis(**analysis_data)
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            logger.info(f"Збережено LLM аналіз: {analysis_data.get('analysis_type')}")
            return analysis
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Помилка збереження LLM аналізу: {e}")
            raise
        finally:
            session.close()
    
    def get_latest_analysis(self, competitor_id: int, analysis_type: str) -> Optional[LLMAnalysis]:
        """Отримати останній аналіз"""
        session = self.get_session()
        try:
            return session.query(LLMAnalysis)\
                .filter_by(competitor_id=competitor_id, analysis_type=analysis_type)\
                .order_by(LLMAnalysis.created_at.desc())\
                .first()
        finally:
            session.close()
    
    # ==================== STATS ====================
    
    def get_competitor_stats(self, competitor_id: int) -> Dict[str, Any]:
        """Отримати статистику по конкуренту"""
        session = self.get_session()
        try:
            competitor = session.query(Competitor).get(competitor_id)
            if not competitor:
                return {}
            
            stats = {
                'competitor_name': competitor.name,
                'competitor_url': competitor.url,
                'total_products': session.query(Product).filter_by(
                    competitor_id=competitor_id, is_active=True
                ).count(),
                'total_promotions': session.query(Promotion).filter_by(
                    competitor_id=competitor_id, is_active=True
                ).count(),
                'last_scan': session.query(ScanHistory)\
                    .filter_by(competitor_id=competitor_id)\
                    .order_by(ScanHistory.completed_at.desc())\
                    .first(),
                'has_seo_data': session.query(SEOData)\
                    .filter_by(competitor_id=competitor_id).count() > 0,
                'has_company_data': session.query(CompanyData)\
                    .filter_by(competitor_id=competitor_id).count() > 0,
            }
            
            return stats
        finally:
            session.close()
