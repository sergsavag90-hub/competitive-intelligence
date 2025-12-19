"""
Модуль для виявлення нових продуктів, акцій та змін у конкурентів
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Детектор змін у даних конкурентів"""
    
    def __init__(self, db_manager):
        """
        Ініціалізація детектора
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
    
    def detect_new_products(
        self, 
        competitor_id: int, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Виявити нові продукти за останній період
        
        Args:
            competitor_id: ID конкурента
            hours: Кількість годин для перевірки
            
        Returns:
            Список нових продуктів
        """
        from src.database.models import Product, Competitor
        
        session = self.db.Session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            new_products = session.query(Product).filter(
                Product.competitor_id == competitor_id,
                Product.first_seen >= cutoff_time,
                Product.is_active == True
            ).order_by(
                Product.first_seen.desc()
            ).all()
            
            competitor = session.query(Competitor).get(competitor_id)
            
            result = []
            for product in new_products:
                result.append({
                    'product_id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'currency': product.currency,
                    'category': product.category,
                    'url': product.url,
                    'in_stock': product.in_stock,
                    'first_seen': product.first_seen.isoformat(),
                    'competitor_name': competitor.name if competitor else None
                })
            
            logger.info(f"Виявлено {len(result)} нових продуктів за останні {hours} годин")
            
            return result
            
        finally:
            session.close()
    
    def detect_new_promotions(
        self, 
        competitor_id: int, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Виявити нові акції за останній період
        
        Args:
            competitor_id: ID конкурента
            hours: Кількість годин для перевірки
            
        Returns:
            Список нових акцій
        """
        from src.database.models import Promotion, Competitor
        
        session = self.db.Session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            new_promotions = session.query(Promotion).filter(
                Promotion.competitor_id == competitor_id,
                Promotion.first_seen >= cutoff_time,
                Promotion.is_active == True
            ).order_by(
                Promotion.first_seen.desc()
            ).all()
            
            competitor = session.query(Competitor).get(competitor_id)
            
            result = []
            for promo in new_promotions:
                result.append({
                    'promotion_id': promo.id,
                    'title': promo.title,
                    'description': promo.description,
                    'promotion_type': promo.promotion_type,
                    'discount_value': promo.discount_value,
                    'discount_type': promo.discount_type,
                    'promo_code': promo.promo_code,
                    'url': promo.url,
                    'start_date': promo.start_date.isoformat() if promo.start_date else None,
                    'end_date': promo.end_date.isoformat() if promo.end_date else None,
                    'first_seen': promo.first_seen.isoformat(),
                    'competitor_name': competitor.name if competitor else None
                })
            
            logger.info(f"Виявлено {len(result)} нових акцій за останні {hours} годин")
            
            return result
            
        finally:
            session.close()
    
    def detect_discontinued_products(
        self, 
        competitor_id: int, 
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Виявити товари, які зникли з продажу
        
        Args:
            competitor_id: ID конкурента
            days: Кількість днів без оновлень
            
        Returns:
            Список товарів, що зникли
        """
        from src.database.models import Product
        
        session = self.db.Session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            discontinued = session.query(Product).filter(
                Product.competitor_id == competitor_id,
                Product.is_active == True,
                Product.last_seen < cutoff_time
            ).order_by(
                Product.last_seen.asc()
            ).all()
            
            result = []
            for product in discontinued:
                result.append({
                    'product_id': product.id,
                    'name': product.name,
                    'category': product.category,
                    'last_price': product.price,
                    'currency': product.currency,
                    'url': product.url,
                    'last_seen': product.last_seen.isoformat(),
                    'days_inactive': (datetime.utcnow() - product.last_seen).days
                })
            
            logger.info(f"Виявлено {len(result)} товарів, що зникли з продажу")
            
            return result
            
        finally:
            session.close()
    
    def detect_price_changes(
        self, 
        competitor_id: int, 
        hours: int = 24,
        min_change_percent: float = 5.0
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Виявити значні зміни цін
        
        Args:
            competitor_id: ID конкурента
            hours: Період для перевірки
            min_change_percent: Мінімальний відсоток зміни для виявлення
            
        Returns:
            Кортеж (список підвищень цін, список знижень цін)
        """
        from src.database.models import Product, PriceHistory
        
        session = self.db.Session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Отримуємо історію цін за період
            price_records = session.query(
                Product.id,
                Product.name,
                Product.category,
                Product.url,
                PriceHistory.price,
                PriceHistory.old_price,
                PriceHistory.recorded_at
            ).join(
                PriceHistory, Product.id == PriceHistory.product_id
            ).filter(
                Product.competitor_id == competitor_id,
                PriceHistory.recorded_at >= cutoff_time
            ).order_by(
                Product.id, PriceHistory.recorded_at
            ).all()
            
            # Групуємо по продуктах
            from collections import defaultdict
            products_history = defaultdict(list)
            
            for record in price_records:
                products_history[record.id].append({
                    'name': record.name,
                    'category': record.category,
                    'url': record.url,
                    'price': record.price,
                    'old_price': record.old_price,
                    'recorded_at': record.recorded_at
                })
            
            price_increases = []
            price_decreases = []
            
            for product_id, history in products_history.items():
                if len(history) < 2:
                    continue
                
                # Перший і останній запис
                first = history[0]
                last = history[-1]
                
                if first['price'] == last['price']:
                    continue
                
                change_percent = ((last['price'] - first['price']) / first['price']) * 100
                
                if abs(change_percent) < min_change_percent:
                    continue
                
                change_info = {
                    'product_id': product_id,
                    'name': last['name'],
                    'category': last['category'],
                    'url': last['url'],
                    'old_price': first['price'],
                    'new_price': last['price'],
                    'change_percent': round(change_percent, 2),
                    'change_absolute': round(last['price'] - first['price'], 2),
                    'detected_at': datetime.utcnow().isoformat()
                }
                
                if change_percent > 0:
                    price_increases.append(change_info)
                else:
                    price_decreases.append(change_info)
            
            # Сортуємо за величиною зміни
            price_increases.sort(key=lambda x: abs(x['change_percent']), reverse=True)
            price_decreases.sort(key=lambda x: abs(x['change_percent']), reverse=True)
            
            logger.info(
                f"Виявлено {len(price_increases)} підвищень та "
                f"{len(price_decreases)} знижень цін"
            )
            
            return price_increases, price_decreases
            
        finally:
            session.close()
    
    def detect_stock_changes(
        self, 
        competitor_id: int, 
        hours: int = 24
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Виявити зміни в наявності товарів
        
        Args:
            competitor_id: ID конкурента
            hours: Період для перевірки
            
        Returns:
            Кортеж (список товарів, що з'явились, список товарів, що закінчились)
        """
        from src.database.models import Product, PriceHistory
        
        session = self.db.Session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Отримуємо зміни наявності
            stock_records = session.query(
                Product.id,
                Product.name,
                Product.category,
                Product.price,
                Product.url,
                PriceHistory.in_stock,
                PriceHistory.recorded_at
            ).join(
                PriceHistory, Product.id == PriceHistory.product_id
            ).filter(
                Product.competitor_id == competitor_id,
                PriceHistory.recorded_at >= cutoff_time
            ).order_by(
                Product.id, PriceHistory.recorded_at
            ).all()
            
            from collections import defaultdict
            products_stock = defaultdict(list)
            
            for record in stock_records:
                products_stock[record.id].append({
                    'name': record.name,
                    'category': record.category,
                    'price': record.price,
                    'url': record.url,
                    'in_stock': record.in_stock,
                    'recorded_at': record.recorded_at
                })
            
            back_in_stock = []
            out_of_stock = []
            
            for product_id, history in products_stock.items():
                if len(history) < 2:
                    continue
                
                first = history[0]
                last = history[-1]
                
                # Товар з'явився в наявності
                if not first['in_stock'] and last['in_stock']:
                    back_in_stock.append({
                        'product_id': product_id,
                        'name': last['name'],
                        'category': last['category'],
                        'price': last['price'],
                        'url': last['url'],
                        'detected_at': last['recorded_at'].isoformat()
                    })
                
                # Товар закінчився
                elif first['in_stock'] and not last['in_stock']:
                    out_of_stock.append({
                        'product_id': product_id,
                        'name': last['name'],
                        'category': last['category'],
                        'price': last['price'],
                        'url': last['url'],
                        'detected_at': last['recorded_at'].isoformat()
                    })
            
            logger.info(
                f"Виявлено {len(back_in_stock)} товарів, що з'явились, та "
                f"{len(out_of_stock)} товарів, що закінчились"
            )
            
            return back_in_stock, out_of_stock
            
        finally:
            session.close()
    
    def get_changes_summary(
        self, 
        competitor_id: int = None, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Отримати загальну інформацію про зміни
        
        Args:
            competitor_id: ID конкурента (якщо None - по всіх)
            hours: Період для аналізу
            
        Returns:
            Словник з узагальненими змінами
        """
        from src.database.models import Competitor
        
        session = self.db.Session()
        try:
            # Визначаємо список конкурентів для аналізу
            if competitor_id:
                competitors = [session.query(Competitor).get(competitor_id)]
            else:
                competitors = session.query(Competitor).filter(
                    Competitor.enabled == True
                ).all()
            
            summary = {
                'period_hours': hours,
                'competitors_analyzed': len(competitors),
                'changes': []
            }
            
            for competitor in competitors:
                comp_changes = {
                    'competitor_id': competitor.id,
                    'competitor_name': competitor.name,
                    'new_products': self.detect_new_products(competitor.id, hours),
                    'new_promotions': self.detect_new_promotions(competitor.id, hours),
                }
                
                # Виявляємо зміни цін
                price_increases, price_decreases = self.detect_price_changes(
                    competitor.id, hours
                )
                comp_changes['price_increases'] = price_increases
                comp_changes['price_decreases'] = price_decreases
                
                # Виявляємо зміни наявності
                back_in_stock, out_of_stock = self.detect_stock_changes(
                    competitor.id, hours
                )
                comp_changes['back_in_stock'] = back_in_stock
                comp_changes['out_of_stock'] = out_of_stock
                
                # Додаємо статистику
                comp_changes['summary'] = {
                    'total_new_products': len(comp_changes['new_products']),
                    'total_new_promotions': len(comp_changes['new_promotions']),
                    'total_price_increases': len(comp_changes['price_increases']),
                    'total_price_decreases': len(comp_changes['price_decreases']),
                    'total_back_in_stock': len(comp_changes['back_in_stock']),
                    'total_out_of_stock': len(comp_changes['out_of_stock'])
                }
                
                summary['changes'].append(comp_changes)
            
            summary['analyzed_at'] = datetime.utcnow().isoformat()
            
            return summary
            
        finally:
            session.close()
