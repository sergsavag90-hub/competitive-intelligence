#!/usr/bin/env python3
"""
Головний скрипт для запуску конкурентної розвідки
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Додаємо src до шляху
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import config
from src.database.db_manager import DatabaseManager
from src.scrapers.seo_scraper import SEOScraper
from src.scrapers.company_scraper import CompanyScraper
from src.scrapers.product_scraper import ProductScraper
from src.scrapers.promotion_scraper import PromotionScraper

# Налаштування логування
def setup_logging(silent: bool = False):
    """Налаштувати логування"""
    log_dir = Path(config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    level = logging.INFO if not silent else logging.WARNING
    
    # Формат логів
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # File handler
    file_handler = logging.FileHandler(config.log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    if not silent:
        root_logger.addHandler(console_handler)


logger = logging.getLogger(__name__)


class CompetitiveIntelligence:
    """Головний клас для конкурентної розвідки"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def run_full_analysis(self, target_name: str = None):
        """Запустити повний аналіз"""
        logger.info("=" * 80)
        logger.info("Запуск повного аналізу конкурентів")
        logger.info("=" * 80)
        
        # Отримуємо список цілей
        targets = config.get_enabled_targets()
        
        if target_name:
            targets = [t for t in targets if t['name'] == target_name]
            if not targets:
                logger.error(f"Ціль '{target_name}' не знайдена")
                return
        
        logger.info(f"Знайдено {len(targets)} цілей для аналізу")
        
        for target in targets:
            self._analyze_competitor(target)
        
        logger.info("=" * 80)
        logger.info("Аналіз завершено!")
        logger.info("=" * 80)
    
    def _analyze_competitor(self, target: dict):
        """Аналізувати одного конкурента"""
        name = target['name']
        url = target['url']
        
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Аналіз конкурента: {name}")
        logger.info(f"URL: {url}")
        logger.info(f"{'=' * 60}\n")
        
        # Додаємо/отримуємо конкурента в БД
        competitor = self.db.get_competitor_by_name(name)
        if not competitor:
            competitor = self.db.add_competitor(
                name=name,
                url=url,
                priority=target.get('priority', 1),
                enabled=target.get('enabled', True)
            )
            logger.info(f"Додано нового конкурента: {name}")
        
        competitor_id = competitor.id
        
        # Початок сканування
        scan = self.db.start_scan(
            competitor_id=competitor_id,
            scan_type='full',
            metadata={'target': name, 'url': url}
        )
        
        total_items = 0
        errors = []
        
        try:
            # Модуль SEO
            if config.is_module_enabled('seo'):
                logger.info("\n📊 Збір SEO даних...")
                try:
                    seo_data = self.run_seo_analysis(url)
                    if seo_data:
                        self.db.save_seo_data(competitor_id, seo_data)
                        total_items += 1
                        logger.info("✓ SEO дані збережено")
                except Exception as e:
                    error_msg = f"SEO помилка: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Модуль Company
            if config.is_module_enabled('company'):
                logger.info("\n🏢 Збір контактних даних...")
                try:
                    company_data = self.run_company_analysis(url)
                    if company_data:
                        self.db.save_company_data(competitor_id, company_data)
                        total_items += 1
                        logger.info("✓ Контактні дані збережено")
                except Exception as e:
                    error_msg = f"Company помилка: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Модуль Products
            if config.is_module_enabled('products'):
                logger.info("\n🛒 Збір товарів/послуг...")
                try:
                    products = self.run_product_analysis(url)
                    for product in products:
                        self.db.add_or_update_product(competitor_id, product)
                    total_items += len(products)
                    logger.info(f"✓ Збережено {len(products)} товарів")
                except Exception as e:
                    error_msg = f"Products помилка: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Модуль Promotions
            if config.is_module_enabled('promotions'):
                logger.info("\n🎁 Збір акцій та промо...")
                try:
                    promotions = self.run_promotion_analysis(url)
                    for promo in promotions:
                        self.db.add_or_update_promotion(competitor_id, promo)
                    total_items += len(promotions)
                    logger.info(f"✓ Збережено {len(promotions)} акцій")
                except Exception as e:
                    error_msg = f"Promotions помилка: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Завершуємо успішно
            status = 'success' if not errors else 'partial'
            error_message = '\n'.join(errors) if errors else None
            
            self.db.complete_scan(
                scan_id=scan.id,
                status=status,
                items_collected=total_items,
                error_message=error_message
            )
            
            logger.info(f"\n✅ Аналіз завершено: {total_items} елементів зібрано")
            
        except Exception as e:
            logger.error(f"Критична помилка аналізу: {e}", exc_info=True)
            self.db.complete_scan(
                scan_id=scan.id,
                status='failed',
                items_collected=total_items,
                error_message=str(e)
            )
    
    def run_seo_analysis(self, url: str):
        """SEO аналіз"""
        scraper = SEOScraper()
        return scraper.scrape(url)
    
    def run_company_analysis(self, url: str):
        """Аналіз контактних даних"""
        scraper = CompanyScraper()
        return scraper.scrape(url)
    
    def run_product_analysis(self, url: str):
        """Аналіз товарів"""
        scraper = ProductScraper()
        return scraper.scrape(url)
    
    def run_promotion_analysis(self, url: str):
        """Аналіз акцій"""
        scraper = PromotionScraper()
        return scraper.scrape(url)


def main():
    """Головна функція"""
    parser = argparse.ArgumentParser(
        description='Інструмент конкурентної розвідки для Selenium Grid'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Запустити повний аналіз всіх конкурентів'
    )
    
    parser.add_argument(
        '--target',
        type=str,
        help='Ім\'я конкретного конкурента для аналізу'
    )
    
    parser.add_argument(
        '--module',
        type=str,
        choices=['seo', 'company', 'products', 'promotions'],
        help='Запустити тільки конкретний модуль'
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='URL для прямого аналізу (без збереження в БД)'
    )
    
    parser.add_argument(
        '--silent',
        action='store_true',
        help='Тихий режим (без виводу в консоль)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Показати статистику по конкурентам'
    )
    
    args = parser.parse_args()
    
    # Налаштовуємо логування
    setup_logging(silent=args.silent)
    
    # Ініціалізуємо CI
    ci = CompetitiveIntelligence()
    
    # Статистика
    if args.stats:
        print_statistics(ci.db)
        return
    
    # Прямий аналіз URL
    if args.url:
        if args.module == 'seo':
            data = ci.run_seo_analysis(args.url)
            print(data)
        elif args.module == 'company':
            data = ci.run_company_analysis(args.url)
            print(data)
        elif args.module == 'products':
            data = ci.run_product_analysis(args.url)
            print(f"Знайдено {len(data)} товарів")
        elif args.module == 'promotions':
            data = ci.run_promotion_analysis(args.url)
            print(f"Знайдено {len(data)} акцій")
        else:
            logger.error("Вкажіть --module для прямого аналізу URL")
        return
    
    # Повний аналіз
    if args.full:
        ci.run_full_analysis(target_name=args.target)
    else:
        parser.print_help()


def print_statistics(db: DatabaseManager):
    """Вивести статистику"""
    print("\n" + "=" * 80)
    print("СТАТИСТИКА КОНКУРЕНТНОЇ РОЗВІДКИ")
    print("=" * 80 + "\n")
    
    competitors = db.get_all_competitors(enabled_only=False)
    
    for competitor in competitors:
        stats = db.get_competitor_stats(competitor.id)
        
        print(f"📊 {stats['competitor_name']}")
        print(f"   URL: {stats['competitor_url']}")
        print(f"   Товарів: {stats['total_products']}")
        print(f"   Акцій: {stats['total_promotions']}")
        print(f"   SEO дані: {'✓' if stats['has_seo_data'] else '✗'}")
        print(f"   Контакти: {'✓' if stats['has_company_data'] else '✗'}")
        
        if stats['last_scan']:
            scan = stats['last_scan']
            print(f"   Останнє сканування: {scan.completed_at} ({scan.status})")
        
        print()


if __name__ == '__main__':
    main()
