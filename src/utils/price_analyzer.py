"""
Модуль для аналізу цінової політики конкурентів
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


class PriceAnalyzer:
    """Аналізатор цінової політики"""
    
    def __init__(self, db_manager):
        """
        Ініціалізація аналізатора
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
    
    def analyze_price_trends(
        self, 
        competitor_id: int, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Аналізувати тренди цін за період
        
        Args:
            competitor_id: ID конкурента
            days: Кількість днів для аналізу
            
        Returns:
            Словник з аналізом трендів
        """
        from src.database.models import Product, PriceHistory
        from sqlalchemy import func
        
        session = self.db.Session()
        try:
            # Отримуємо історію цін за період
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            price_changes = session.query(
                Product.id,
                Product.name,
                Product.category,
                PriceHistory.price,
                PriceHistory.old_price,
                PriceHistory.recorded_at
            ).join(
                PriceHistory, Product.id == PriceHistory.product_id
            ).filter(
                Product.competitor_id == competitor_id,
                PriceHistory.recorded_at >= cutoff_date
            ).order_by(
                Product.id, PriceHistory.recorded_at
            ).all()
            
            # Групуємо по продуктах
            products_data = defaultdict(list)
            for change in price_changes:
                products_data[change.id].append({
                    'name': change.name,
                    'category': change.category,
                    'price': change.price,
                    'old_price': change.old_price,
                    'date': change.recorded_at
                })
            
            # Аналізуємо тренди
            trends = {
                'increasing': [],
                'decreasing': [],
                'stable': [],
                'volatile': []
            }
            
            for product_id, history in products_data.items():
                if len(history) < 2:
                    continue
                
                prices = [h['price'] for h in history]
                first_price = prices[0]
                last_price = prices[-1]
                
                # Обчислюємо зміну ціни
                price_change = ((last_price - first_price) / first_price) * 100
                
                # Обчислюємо волатильність
                if len(prices) > 2:
                    price_std = statistics.stdev(prices)
                    volatility = (price_std / statistics.mean(prices)) * 100
                else:
                    volatility = 0
                
                product_info = {
                    'product_id': product_id,
                    'name': history[0]['name'],
                    'category': history[0]['category'],
                    'first_price': first_price,
                    'last_price': last_price,
                    'price_change_percent': round(price_change, 2),
                    'volatility_percent': round(volatility, 2),
                    'data_points': len(history)
                }
                
                # Класифікуємо тренд
                if volatility > 10:
                    trends['volatile'].append(product_info)
                elif price_change > 5:
                    trends['increasing'].append(product_info)
                elif price_change < -5:
                    trends['decreasing'].append(product_info)
                else:
                    trends['stable'].append(product_info)
            
            # Сортуємо за величиною зміни
            for key in trends:
                trends[key].sort(
                    key=lambda x: abs(x['price_change_percent']), 
                    reverse=True
                )
            
            # Загальна статистика
            all_products = sum([len(v) for v in trends.values()])
            
            summary = {
                'period_days': days,
                'total_products_analyzed': all_products,
                'increasing_count': len(trends['increasing']),
                'decreasing_count': len(trends['decreasing']),
                'stable_count': len(trends['stable']),
                'volatile_count': len(trends['volatile'])
            }
            
            return {
                'summary': summary,
                'trends': trends,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        finally:
            session.close()
    
    def compare_prices_with_competitors(
        self,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Порівняти ціни між конкурентами
        
        Args:
            category: Фільтр по категорії (опціонально)
            
        Returns:
            Словник з порівнянням цін
        """
        from src.database.models import Product, Competitor
        
        session = self.db.Session()
        try:
            # Отримуємо актуальні товари
            query = session.query(
                Product.name,
                Product.category,
                Product.price,
                Product.currency,
                Competitor.name.label('competitor_name'),
                Competitor.id.label('competitor_id')
            ).join(
                Competitor, Product.competitor_id == Competitor.id
            ).filter(
                Product.is_active == True,
                Product.price.isnot(None)
            )
            
            if category:
                query = query.filter(Product.category == category)
            
            products = query.all()
            
            # Групуємо схожі товари по назві (спрощено)
            products_by_name = defaultdict(list)
            for p in products:
                # Нормалізуємо назву для порівняння
                normalized_name = p.name.lower().strip()
                products_by_name[normalized_name].append({
                    'competitor_id': p.competitor_id,
                    'competitor_name': p.competitor_name,
                    'price': p.price,
                    'currency': p.currency,
                    'category': p.category
                })
            
            # Знаходимо товари з розривами в цінах
            price_gaps = []
            
            for name, items in products_by_name.items():
                if len(items) < 2:
                    continue
                
                # Сортуємо по ціні
                items_sorted = sorted(items, key=lambda x: x['price'])
                
                min_price = items_sorted[0]['price']
                max_price = items_sorted[-1]['price']
                price_diff = max_price - min_price
                price_diff_percent = (price_diff / min_price) * 100
                
                if price_diff_percent > 10:  # Розрив більше 10%
                    price_gaps.append({
                        'product_name': name,
                        'category': items[0]['category'],
                        'min_price': min_price,
                        'max_price': max_price,
                        'price_difference': round(price_diff, 2),
                        'price_difference_percent': round(price_diff_percent, 2),
                        'cheapest_competitor': items_sorted[0]['competitor_name'],
                        'most_expensive_competitor': items_sorted[-1]['competitor_name'],
                        'total_competitors': len(items)
                    })
            
            # Сортуємо за величиною розриву
            price_gaps.sort(key=lambda x: x['price_difference_percent'], reverse=True)
            
            # Статистика по конкурентах
            competitor_stats = defaultdict(lambda: {'total': 0, 'sum': 0, 'min': float('inf'), 'max': 0})
            
            for items in products_by_name.values():
                for item in items:
                    comp_id = item['competitor_id']
                    price = item['price']
                    competitor_stats[comp_id]['total'] += 1
                    competitor_stats[comp_id]['sum'] += price
                    competitor_stats[comp_id]['min'] = min(competitor_stats[comp_id]['min'], price)
                    competitor_stats[comp_id]['max'] = max(competitor_stats[comp_id]['max'], price)
                    if 'name' not in competitor_stats[comp_id]:
                        competitor_stats[comp_id]['name'] = item['competitor_name']
            
            # Обчислюємо середні ціни
            for comp_id, stats in competitor_stats.items():
                stats['average_price'] = round(stats['sum'] / stats['total'], 2)
            
            return {
                'price_gaps': price_gaps[:50],  # Топ 50 розривів
                'competitor_stats': dict(competitor_stats),
                'total_products_compared': len(products_by_name),
                'category_filter': category,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        finally:
            session.close()
    
    def detect_pricing_strategy(self, competitor_id: int) -> Dict[str, Any]:
        """
        Визначити цінову стратегію конкурента
        
        Args:
            competitor_id: ID конкурента
            
        Returns:
            Словник з аналізом стратегії
        """
        from src.database.models import Product
        
        session = self.db.Session()
        try:
            # Отримуємо всі активні товари
            products = session.query(Product).filter(
                Product.competitor_id == competitor_id,
                Product.is_active == True,
                Product.price.isnot(None)
            ).all()
            
            if not products:
                return {'error': 'No products found'}
            
            prices = [p.price for p in products]
            discounted = [p for p in products if p.old_price and p.old_price > p.price]
            
            # Статистика
            avg_price = statistics.mean(prices)
            median_price = statistics.median(prices)
            
            # Відсоток товарів зі знижками
            discount_rate = (len(discounted) / len(products)) * 100
            
            # Середній розмір знижки
            if discounted:
                avg_discount = statistics.mean([
                    ((p.old_price - p.price) / p.old_price) * 100 
                    for p in discounted
                ])
            else:
                avg_discount = 0
            
            # Визначаємо стратегію
            strategy = 'unknown'
            strategy_confidence = 0
            
            if discount_rate > 50:
                strategy = 'aggressive_discounting'
                strategy_confidence = min(discount_rate, 100)
            elif discount_rate > 20:
                strategy = 'moderate_discounting'
                strategy_confidence = discount_rate
            elif avg_price < median_price * 0.8:
                strategy = 'low_price_leader'
                strategy_confidence = 70
            elif avg_price > median_price * 1.2:
                strategy = 'premium_pricing'
                strategy_confidence = 70
            else:
                strategy = 'market_based_pricing'
                strategy_confidence = 60
            
            return {
                'strategy': strategy,
                'confidence': round(strategy_confidence, 2),
                'statistics': {
                    'total_products': len(products),
                    'average_price': round(avg_price, 2),
                    'median_price': round(median_price, 2),
                    'min_price': min(prices),
                    'max_price': max(prices),
                    'products_with_discount': len(discounted),
                    'discount_rate_percent': round(discount_rate, 2),
                    'average_discount_percent': round(avg_discount, 2)
                },
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        finally:
            session.close()
    
    def get_price_optimization_recommendations(
        self,
        competitor_id: int
    ) -> List[Dict[str, Any]]:
        """
        Отримати рекомендації по оптимізації цін
        
        Args:
            competitor_id: ID конкурента для порівняння
            
        Returns:
            Список рекомендацій
        """
        recommendations = []
        
        # Аналізуємо тренди
        trends = self.analyze_price_trends(competitor_id, days=30)
        
        # Рекомендації на основі трендів
        if trends['summary']['increasing_count'] > trends['summary']['decreasing_count']:
            recommendations.append({
                'type': 'pricing_trend',
                'priority': 'high',
                'title': 'Конкурент підвищує ціни',
                'description': f"Виявлено {trends['summary']['increasing_count']} товарів з підвищенням цін. "
                              "Розгляньте можливість підвищення власних цін або акцентування на вигідності.",
                'affected_products': trends['summary']['increasing_count']
            })
        
        if trends['summary']['volatile_count'] > 5:
            recommendations.append({
                'type': 'price_volatility',
                'priority': 'medium',
                'title': 'Високу волатильність цін',
                'description': f"Виявлено {trends['summary']['volatile_count']} товарів з нестабільними цінами. "
                              "Це може свідчити про тестування цін або проблеми з постачанням.",
                'affected_products': trends['summary']['volatile_count']
            })
        
        # Порівняння з конкурентами
        comparison = self.compare_prices_with_competitors()
        
        if comparison['price_gaps']:
            top_gaps = comparison['price_gaps'][:5]
            recommendations.append({
                'type': 'price_gaps',
                'priority': 'high',
                'title': 'Виявлено значні цінові розриви',
                'description': f"Знайдено {len(comparison['price_gaps'])} товарів з розривом цін > 10%. "
                              "Розгляньте можливість корекції цін на ці товари.",
                'top_products': [
                    {
                        'name': gap['product_name'],
                        'difference': gap['price_difference_percent']
                    }
                    for gap in top_gaps
                ]
            })
        
        # Аналізуємо стратегію
        strategy = self.detect_pricing_strategy(competitor_id)
        
        if strategy.get('strategy') == 'aggressive_discounting':
            recommendations.append({
                'type': 'pricing_strategy',
                'priority': 'high',
                'title': 'Конкурент використовує агресивну стратегію знижок',
                'description': f"Більше 50% товарів зі знижками (середня знижка: "
                              f"{strategy['statistics']['average_discount_percent']:.1f}%). "
                              "Розгляньте запуск власних промо-акцій.",
                'discount_rate': strategy['statistics']['discount_rate_percent']
            })
        
        return recommendations
