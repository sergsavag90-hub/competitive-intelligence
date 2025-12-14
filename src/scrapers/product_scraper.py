"""
Product Scraper - збір товарів та послуг
"""

import logging
import re
from typing import Dict, Any, List, Set, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from selenium.webdriver.common.by import By

from ..utils.selenium_helper import SeleniumHelper
from ..utils.config import config

logger = logging.getLogger(__name__)


class ProductScraper(SeleniumHelper):
    """Клас для збору товарів/послуг з сайту"""
    
    def scrape(self, url: str, max_products: int = None) -> List[Dict[str, Any]]:
        """Зібрати товари/послуги з сайту"""
        if max_products is None:
            max_products = config.get('modules.products.max_products_per_site', 1000)
        
        logger.info(f"Збір товарів з {url} (макс: {max_products})")
        
        products = []
        seen_products: Set[str] = set()
        
        try:
            if not self.safe_get(url):
                logger.error(f"Не вдалося завантажити {url}")
                return products
            
            # Знаходимо каталог/магазин
            catalog_urls = self._find_catalog_urls(url)
            
            if not catalog_urls:
                logger.warning("Не знайдено сторінок каталогу")
                # Спробуємо обробити головну сторінку
                catalog_urls = [url]
            
            # Обробляємо кожну сторінку каталогу
            for catalog_url in catalog_urls[:5]:  # Обмежуємо кількість сторінок
                if len(products) >= max_products:
                    break
                
                logger.info(f"Обробка каталогу: {catalog_url}")
                page_products = self._scrape_catalog_page(catalog_url)
                for item in page_products:
                    unique_key = item.get('url') or item.get('name')
                    if not unique_key:
                        continue
                    if unique_key in seen_products:
                        continue
                    seen_products.add(unique_key)
                    products.append(item)
            
            logger.info(f"Зібрано {len(products)} товарів")
            
        except Exception as e:
            logger.error(f"Помилка збору товарів: {e}", exc_info=True)
        
        finally:
            self.close_driver()
        
        return products[:max_products]
    
    def _find_catalog_urls(self, base_url: str) -> List[str]:
        """Знайти URL каталогу/магазину"""
        catalog_urls = []
        
        try:
            page_source = self.get_page_source()
            if not page_source:
                return catalog_urls
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Ключові слова для пошуку
            keywords = [
                'catalog', 'shop', 'store', 'products', 'goods',
                'каталог', 'магазин', 'товари', 'продукція', 'послуги'
            ]
            
            # Шукаємо посилання з ключовими словами
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Перевіряємо текст посилання або URL
                if any(keyword in text for keyword in keywords) or \
                   any(keyword in href.lower() for keyword in keywords):
                    absolute_url = urljoin(base_url, href)
                    
                    # Уникаємо дублікатів
                    if absolute_url not in catalog_urls and \
                       urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                        catalog_urls.append(absolute_url)
                        
                        if len(catalog_urls) >= 10:
                            break
        
        except Exception as e:
            logger.debug(f"Помилка пошуку каталогу: {e}")
        
        return catalog_urls
    
    def _extract_category_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Отримати назву категорії зі сторінки"""
        title = soup.find('h1', class_=re.compile(r'category', re.I))
        if title:
            return title.get_text(strip=True)
        
        breadcrumb = soup.find('ul', class_=re.compile(r'bread', re.I))
        if breadcrumb:
            items = breadcrumb.find_all('li')
            if items:
                text = items[-1].get_text(strip=True)
                if text:
                    return text
        
        return None
    
    def _scrape_catalog_page(self, url: str) -> List[Dict[str, Any]]:
        """Обробити сторінку каталогу"""
        products = []
        
        try:
            if not self.safe_get(url):
                return products
            
            page_source = self.get_page_source()
            if not page_source:
                return products
            soup = BeautifulSoup(page_source, 'lxml')
            category_name = self._extract_category_name(soup)
            
            # Знаходимо товари на сторінці
            product_elements = self._find_product_elements(soup)
            
            logger.info(f"Знайдено {len(product_elements)} товарів на сторінці")
            
            for elem in product_elements:
                product_data = self._parse_product_element(elem, url)
                if product_data and product_data.get('name'):
                    if category_name and not product_data.get('category'):
                        product_data['category'] = category_name
                    products.append(product_data)
        
        except Exception as e:
            logger.error(f"Помилка обробки каталогу {url}: {e}")
        
        return products
    
    def _find_product_elements(self, soup: BeautifulSoup) -> List:
        """Знайти елементи товарів на сторінці"""
        # Перш за все шукаємо картки, які явно позначені data-product-id
        targeted = soup.find_all(lambda tag: tag.has_attr('data-product-id') and 'product-card' in (tag.get('class') or []))
        if targeted:
            return targeted[:100]
        
        # Потім шукаємо будь-які елементи з data-product-id
        targeted = soup.find_all(attrs={'data-product-id': True})
        if targeted:
            return targeted[:100]
        
        # Далі аналізуємо контейнери, що виглядають як картки товарів
        product_elements = []
        selectors = [
            re.compile(r'\bproduct-card\b', re.I),
            re.compile(r'\bproduct-thumb\b', re.I),
            re.compile(r'\bproduct-item\b', re.I),
        ]
        
        for selector in selectors:
            elements = soup.find_all('div', class_=selector)
            if elements:
                product_elements.extend(elements)
        
        if product_elements:
            return product_elements[:100]
        
        # Фолбек на старий евристичний підхід
        potential_containers = soup.find_all(['div', 'article', 'li'])
        for container in potential_containers[:200]:
            if self._has_product_structure(container):
                product_elements.append(container)
                if len(product_elements) >= 100:
                    break
        
        return product_elements
    
    def _has_product_structure(self, element) -> bool:
        """Перевірити чи має елемент структуру товару"""
        text = element.get_text().lower()
        
        # Повинна бути ціна
        has_price = bool(re.search(r'[\$€£₴]\s*\d+|грн|uah|usd|eur', text, re.I))
        
        # Повинна бути назва/заголовок
        has_title = element.find(['h1', 'h2', 'h3', 'h4', 'a'])
        
        # Бажано зображення
        has_image = element.find('img')
        
        return has_price and has_title
    
    def _parse_product_element(self, element, base_url: str) -> Dict[str, Any]:
        """Парсити дані товару з елемента"""
        product = {
            'name': None,
            'sku': None,
            'url': None,
            'category': None,
            'subcategory': None,
            'price': None,
            'currency': None,
            'old_price': None,
            'discount_percent': None,
            'description': None,
            'short_description': None,
            'specifications': {},
            'main_image': None,
            'images': [],
            'in_stock': True,
            'stock_quantity': None,
            'available_for_order': True,
            'rating': None,
            'reviews_count': None,
        }
        
        try:
            # Назва товару
            product['name'] = self._extract_product_name(element)
            
            # URL товару
            link = element.find('a', class_=re.compile(r'card-name', re.I))
            if not link:
                link = element.find('a', href=True)
            if link:
                product['url'] = urljoin(base_url, link.get('href'))
            
            # Ціна
            price_data = self._extract_price(element)
            product.update(price_data)
            
            # Зображення
            image_data = self._extract_images(element, base_url)
            product.update(image_data)
            
            # Варіанти кольорів
            colors = self._extract_colors(element)
            if colors:
                product['specifications']['colors'] = colors
            
            # SKU
            product['sku'] = self._extract_sku(element)
            
            # Опис
            product['short_description'] = self._extract_description(element)
            
            # Наявність
            product['in_stock'] = self._check_availability(element)
            
            # Рейтинг
            rating_data = self._extract_rating(element)
            product.update(rating_data)
            
        except Exception as e:
            logger.debug(f"Помилка парсингу товару: {e}")
        
        return product
    
    def _extract_product_name(self, element) -> str:
        """Витягти назву товару"""
        # Спеціальна назва з картки
        card_name = element.find(class_=re.compile(r'card-name', re.I))
        if card_name:
            text = card_name.get_text(strip=True)
            if text:
                return text
        
        # Schema.org
        name_tag = element.find(attrs={'itemprop': 'name'})
        if name_tag:
            return name_tag.get_text(strip=True)
        
        # Заголовки
        for tag in ['h1', 'h2', 'h3', 'h4']:
            heading = element.find(tag)
            if heading:
                text = heading.get_text(strip=True)
                if text and len(text) > 3:
                    return text
        
        # Посилання
        link = element.find('a')
        if link:
            title = link.get('title', '').strip()
            if title:
                return title
            text = link.get_text(strip=True)
            if text:
                return text
        
        return None
    
    def _extract_price(self, element) -> Dict:
        """Витягти ціну"""
        price_data = {
            'price': None,
            'currency': None,
            'old_price': None,
            'discount_percent': None,
        }
        
        # Значення прямо з картки
        card_price = element.find(class_=re.compile(r'card-price', re.I))
        if card_price:
            card_price_text = card_price.get_text(strip=True)
            price_data['price'] = self._parse_price_string(card_price_text)
            price_data['currency'] = self._detect_currency(card_price_text)
        
        card_old_price = element.find(class_=re.compile(r'old-price', re.I))
        if card_old_price:
            old_text = card_old_price.get_text(strip=True)
            price_data['old_price'] = self._parse_price_string(old_text)
            if not price_data['currency']:
                price_data['currency'] = self._detect_currency(old_text)
        
        # Schema.org
        price_tag = element.find(attrs={'itemprop': 'price'})
        if price_tag and not price_data['price']:
            price_str = price_tag.get('content') or price_tag.get_text(strip=True)
            price_data['price'] = self._parse_price_string(price_str)
        
        # Шукаємо в тексті
        if not price_data['price']:
            text = element.get_text()
            
            price_patterns = [
                r'([\d\s]+[.,]\d{2})\s*(?:грн|₴|UAH)',
                r'([\d\s]+)\s*(?:грн|₴|UAH)',
                r'[\$€£]\s*([\d\s,]+\.?\d*)',
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    price_data['price'] = self._parse_price_string(match.group(1))
                    break
        
        # Валюта
        if not price_data['currency']:
            text = element.get_text()
            price_data['currency'] = self._detect_currency(text)
        
        # Стара ціна (знижка)
        if price_data['old_price'] is None:
            text = element.get_text()
            old_price_keywords = ['старая', 'стара', 'old', 'was']
            if any(keyword in text.lower() for keyword in old_price_keywords):
                prices = re.findall(r'([\d\s]+[.,]?\d*)\s*(?:грн|₴|UAH)', text, re.I)
                if len(prices) >= 2:
                    price_data['old_price'] = self._parse_price_string(prices[1])
        
        # Розрахунок знижки
        if price_data['price'] and price_data['old_price']:
            if price_data['old_price'] > price_data['price']:
                discount = ((price_data['old_price'] - price_data['price']) / price_data['old_price']) * 100
                price_data['discount_percent'] = round(discount, 2)
        
        return price_data
    
    def _detect_currency(self, text: str) -> Optional[str]:
        """Визначити валюту за текстом"""
        lowered = text.lower()
        if 'грн' in lowered or 'uah' in lowered or '₴' in text:
            return 'UAH'
        if 'usd' in lowered or '$' in text:
            return 'USD'
        if 'eur' in lowered or '€' in text:
            return 'EUR'
        return None
    
    def _parse_price_string(self, price_str: str) -> float:
        """Перетворити рядок ціни в число"""
        try:
            # Очищаємо рядок
            clean_str = re.sub(r'[^\d.,]', '', price_str)
            clean_str = clean_str.replace(',', '.').replace(' ', '')
            return float(clean_str)
        except:
            return None
    
    def _extract_images(self, element, base_url: str) -> Dict:
        """Витягти зображення"""
        image_data = {
            'main_image': None,
            'images': [],
        }
        
        images = element.find_all('img')
        
        for img in images:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src:
                absolute_url = urljoin(base_url, src)
                image_data['images'].append(absolute_url)
        
        if image_data['images']:
            image_data['main_image'] = image_data['images'][0]
        
        return image_data
    
    def _extract_colors(self, element) -> List[str]:
        """Зібрати доступні варіанти кольорів"""
        colors: List[str] = []
        color_elements = element.find_all(class_=re.compile(r'card-color-item', re.I))
        
        for color in color_elements:
            style = color.get('style', '')
            match = re.search(r'--colorValue:\s*([^;]+)', style)
            if match:
                value = match.group(1).strip()
                colors.append(value)
            else:
                text = color.get_text(strip=True)
                if text:
                    colors.append(text)
        
        # Уникаємо повторів
        unique_colors = []
        for value in colors:
            if value not in unique_colors:
                unique_colors.append(value)
        
        return unique_colors
    
    def _extract_sku(self, element) -> str:
        """Витягти артикул"""
        # Schema.org
        sku_tag = element.find(attrs={'itemprop': 'sku'})
        if sku_tag:
            return sku_tag.get_text(strip=True)
        
        # Пошук в тексті
        text = element.get_text()
        sku_match = re.search(r'(?:SKU|Артикул|Код)[:\s]*([A-Z0-9-]+)', text, re.I)
        if sku_match:
            return sku_match.group(1)
        
        return None
    
    def _extract_description(self, element) -> str:
        """Витягти опис"""
        # Schema.org
        desc_tag = element.find(attrs={'itemprop': 'description'})
        if desc_tag:
            text = desc_tag.get_text(strip=True)
            if text:
                return text[:500]  # Обмежуємо довжину
        
        # Загальний опис
        text = element.get_text(strip=True)
        if 50 < len(text) < 1000:
            return text[:500]
        
        return None
    
    def _check_availability(self, element) -> bool:
        """Перевірити наявність"""
        text = element.get_text().lower()
        
        out_of_stock_keywords = [
            'немає в наявності', 'нет в наличии', 'out of stock',
            'sold out', 'недоступно', 'unavailable', 'закінчився'
        ]
        
        return not any(keyword in text for keyword in out_of_stock_keywords)
    
    def _extract_rating(self, element) -> Dict:
        """Витягти рейтинг"""
        rating_data = {
            'rating': None,
            'reviews_count': None,
        }
        
        # Schema.org
        rating_tag = element.find(attrs={'itemprop': 'ratingValue'})
        if rating_tag:
            try:
                rating_data['rating'] = float(rating_tag.get('content') or rating_tag.get_text(strip=True))
            except:
                pass
        
        review_tag = element.find(attrs={'itemprop': 'reviewCount'})
        if review_tag:
            try:
                rating_data['reviews_count'] = int(review_tag.get('content') or review_tag.get_text(strip=True))
            except:
                pass
        
        return rating_data
