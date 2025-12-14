"""
Promotion Scraper - збір акцій та спеціальних пропозицій
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from ..utils.selenium_helper import SeleniumHelper
from ..utils.config import config

logger = logging.getLogger(__name__)


class PromotionScraper(SeleniumHelper):
    """Клас для збору акцій та промо"""
    
    def scrape(self, url: str) -> List[Dict[str, Any]]:
        """Зібрати акції з сайту"""
        logger.info(f"Збір акцій з {url}")
        
        promotions = []
        
        try:
            if not self.safe_get(url):
                logger.error(f"Не вдалося завантажити {url}")
                return promotions
            
            # Знаходимо сторінки з акціями
            promo_urls = self._find_promotion_pages(url)
            
            if not promo_urls:
                # Якщо не знайшли спеціальних сторінок, обробимо головну
                promo_urls = [url]
            
            # Обробляємо кожну сторінку
            for promo_url in promo_urls[:5]:
                logger.info(f"Обробка сторінки акцій: {promo_url}")
                page_promos = self._scrape_promotions_page(promo_url)
                promotions.extend(page_promos)
            
            logger.info(f"Зібрано {len(promotions)} акцій")
            
        except Exception as e:
            logger.error(f"Помилка збору акцій: {e}", exc_info=True)
        
        finally:
            self.close_driver()
        
        return promotions
    
    def _find_promotion_pages(self, base_url: str) -> List[str]:
        """Знайти сторінки з акціями"""
        promo_urls = []
        
        try:
            page_source = self.get_page_source()
            if not page_source:
                return promo_urls
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Ключові слова
            keywords = config.get('modules.promotions.keywords', [
                'знижка', 'акція', 'розпродаж', 'sale', 'discount', 
                'promotion', 'special', 'offer', 'deals'
            ])
            
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Перевіряємо текст або URL
                if any(keyword.lower() in text or keyword.lower() in href.lower() 
                       for keyword in keywords):
                    absolute_url = urljoin(base_url, href)
                    
                    if absolute_url not in promo_urls:
                        promo_urls.append(absolute_url)
                        
                        if len(promo_urls) >= 5:
                            break
        
        except Exception as e:
            logger.debug(f"Помилка пошуку сторінок акцій: {e}")
        
        return promo_urls
    
    def _scrape_promotions_page(self, url: str) -> List[Dict[str, Any]]:
        """Обробити сторінку з акціями"""
        promotions = []
        
        try:
            if not self.safe_get(url):
                return promotions
            
            page_source = self.get_page_source()
            if not page_source:
                return promotions
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Знаходимо елементи акцій
            promo_elements = self._find_promotion_elements(soup)
            
            logger.info(f"Знайдено {len(promo_elements)} акцій на сторінці")
            
            for elem in promo_elements:
                promo_data = self._parse_promotion_element(elem, url)
                if promo_data and promo_data.get('title'):
                    promotions.append(promo_data)
        
        except Exception as e:
            logger.error(f"Помилка обробки сторінки акцій: {e}")
        
        return promotions
    
    def _find_promotion_elements(self, soup: BeautifulSoup) -> List:
        """Знайти елементи акцій"""
        # Спочатку шукаємо картки товарів зі знижкою
        sale_cards = []
        product_cards = soup.find_all(lambda tag: tag.has_attr('class') and 'product-card' in (tag.get('class') or []))
        for card in product_cards:
            if card.find(class_=re.compile(r'sale-label', re.I)):
                sale_cards.append(card)
        
        if sale_cards:
            return sale_cards[:50]
        
        promo_elements = []
        
        # Спробуємо різні селектори
        selectors = [
            {'class': re.compile(r'promo|promotion|sale|discount|offer|deal|акц', re.I)},
            {'data-promo': True},
            {'data-promotion': True},
        ]
        
        for selector in selectors:
            elements = soup.find_all(attrs=selector)
            for elem in elements:
                card_parent = elem.find_parent(class_=re.compile(r'product-card', re.I))
                if card_parent and card_parent not in promo_elements:
                    promo_elements.append(card_parent)
                elif elem not in promo_elements:
                    promo_elements.append(elem)
        
        # Шукаємо за ключовими словами в тексті
        keywords = config.get('modules.promotions.keywords', [])
        
        for keyword in keywords:
            elements = soup.find_all(string=re.compile(keyword, re.I))
            for elem in elements:
                parent = elem.parent
                # Піднімаємося на 2-3 рівні вгору
                for _ in range(3):
                    if parent:
                        if parent.has_attr('class') and 'product-card' in (parent.get('class') or []):
                            if parent not in promo_elements:
                                promo_elements.append(parent)
                            break
                        if parent.name in ['div', 'article', 'section']:
                            if parent not in promo_elements:
                                promo_elements.append(parent)
                            break
                    if parent:
                        parent = parent.parent
        
        return promo_elements[:50]
    
    def _parse_promotion_element(self, element, base_url: str) -> Dict[str, Any]:
        """Парсити дані акції"""
        promo = {
            'title': None,
            'description': None,
            'url': None,
            'promotion_type': None,
            'discount_value': None,
            'discount_type': None,
            'promo_code': None,
            'terms_and_conditions': None,
            'minimum_purchase': None,
            'applicable_categories': [],
            'start_date': None,
            'end_date': None,
            'is_active': True,
            'image_url': None,
        }
        
        try:
            # Заголовок
            promo['title'] = self._extract_card_name(element)
            if not promo['title']:
                promo['title'] = self._extract_promo_title(element)
            
            # URL
            link = element.find('a', href=True)
            if link:
                promo['url'] = urljoin(base_url, link.get('href'))
            else:
                promo['url'] = base_url
            
            # Опис
            promo['description'] = self._extract_promo_description(element)
            self._append_price_description(promo, element)
            
            # Тип та знижка
            discount_data = self._extract_discount_info(element)
            promo.update(discount_data)
            
            # Промо-код
            promo['promo_code'] = self._extract_promo_code(element)
            
            # Дати
            dates = self._extract_dates(element)
            promo.update(dates)
            
            # Зображення
            img = element.find('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    promo['image_url'] = urljoin(base_url, src)
            if not promo['image_url']:
                card_img = element.find('img', attrs={'data-pagespeed-lazy-src': True})
                if card_img:
                    src = card_img.get('data-pagespeed-lazy-src')
                    if src:
                        promo['image_url'] = urljoin(base_url, src)
            
            # Умови
            promo['terms_and_conditions'] = self._extract_terms(element)
            
        except Exception as e:
            logger.debug(f"Помилка парсингу акції: {e}")
        
        return promo
    
    def _extract_card_name(self, element) -> Optional[str]:
        """Отримати назву товару з картки"""
        card_name = element.find(class_=re.compile(r'card-name', re.I))
        if card_name:
            text = card_name.get_text(strip=True)
            if text:
                return text
        return None
    
    def _extract_promo_title(self, element) -> str:
        """Витягти заголовок акції"""
        # Заголовки
        for tag in ['h1', 'h2', 'h3', 'h4']:
            heading = element.find(tag)
            if heading:
                text = heading.get_text(strip=True)
                if text and len(text) > 3:
                    return text
        
        # Жирний текст
        strong = element.find('strong')
        if strong:
            text = strong.get_text(strip=True)
            if text and len(text) > 3:
                return text
        
        # Посилання
        link = element.find('a')
        if link:
            title = link.get('title', '').strip()
            if title:
                return title
        
        # Перші слова тексту
        text = element.get_text(" ", strip=True)
        if text:
            words = text.split()[:10]
            return ' '.join(words)
        
        return None
    
    def _append_price_description(self, promo: Dict[str, Any], element) -> None:
        """Додати інформацію про ціну до опису акції"""
        price_text = self._extract_price_text(element)
        if not price_text:
            return
        
        snippet = f"Поточна ціна: {price_text}"
        if promo['description']:
            promo['description'] = f"{promo['description']} | {snippet}"
        else:
            promo['description'] = snippet
    
    def _extract_price_text(self, element) -> Optional[str]:
        """Повернути текст ціни з картки акції"""
        card_price = element.find(class_=re.compile(r'card-price', re.I))
        if card_price:
            price_text = card_price.get_text(strip=True)
            if price_text:
                return price_text
        return None
    
    def _extract_promo_description(self, element) -> str:
        """Витягти опис акції"""
        # Шукаємо параграфи
        paragraphs = element.find_all('p')
        if paragraphs:
            descriptions = [p.get_text(" ", strip=True) for p in paragraphs if p.get_text(strip=True)]
            if descriptions:
                return ' '.join(descriptions)[:1000]
        
        # Загальний текст
        text = element.get_text(" ", strip=True)
        if 20 < len(text) < 2000:
            return text[:1000]
        
        return None
    
    def _extract_discount_info(self, element) -> Dict:
        """Витягти інформацію про знижку"""
        discount_data = {
            'promotion_type': 'discount',
            'discount_value': None,
            'discount_type': None,
        }
        
        sale_badge = element.find(class_=re.compile(r'sale-label', re.I))
        if sale_badge:
            badge_text = sale_badge.get_text(strip=True)
            percent_match = re.search(r'(-?\d+)\s*%', badge_text)
            if percent_match:
                discount_data['discount_value'] = float(percent_match.group(1))
                discount_data['discount_type'] = 'percent'
                discount_data['promotion_type'] = 'sale'
            else:
                value = re.sub(r'[^\d]', '', badge_text)
                if value:
                    discount_data['discount_value'] = float(value)
                    discount_data['discount_type'] = 'fixed'
                    discount_data['promotion_type'] = 'sale'
        
        text = element.get_text()
        
        # Шукаємо відсоток знижки
        percent_match = None
        if not discount_data['discount_value']:
            percent_match = re.search(r'(\d+)\s*%', text)
            if percent_match:
                discount_data['discount_value'] = float(percent_match.group(1))
                discount_data['discount_type'] = 'percent'
        
        # Фіксована знижка
        if discount_data['discount_value'] is None:
            fixed_patterns = [
                r'знижка\s*(\d+)\s*(?:грн|₴)',
                r'discount\s*(\d+)\s*(?:uah|грн)',
                r'[\-]\s*(\d+)\s*(?:грн|₴)'
            ]
            
            for pattern in fixed_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    discount_data['discount_value'] = float(match.group(1))
                    discount_data['discount_type'] = 'fixed'
                    break
        
        # Безкоштовна доставка
        free_shipping_keywords = ['безкоштовна доставка', 'free shipping', 'free delivery']
        if any(keyword in text.lower() for keyword in free_shipping_keywords):
            discount_data['promotion_type'] = 'free_shipping'
        
        # Розпродаж
        if any(word in text.lower() for word in ['розпродаж', 'sale', 'clearance']):
            discount_data['promotion_type'] = 'sale'
        
        # Спеціальна пропозиція
        if any(word in text.lower() for word in ['спеціальна пропозиція', 'special offer']):
            discount_data['promotion_type'] = 'special_offer'
        
        return discount_data
    
    def _extract_promo_code(self, element) -> str:
        """Витягти промо-код"""
        text = element.get_text()
        
        # Шукаємо промо-код
        patterns = [
            r'(?:код|code|промокод|promo)[:\s]*([A-Z0-9]{4,20})',
            r'(?:використай|use)[:\s]*([A-Z0-9]{4,20})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _extract_dates(self, element) -> Dict:
        """Витягти дати акції"""
        dates = {
            'start_date': None,
            'end_date': None,
        }
        
        text = element.get_text()
        
        # Шукаємо дати у форматі DD.MM.YYYY або DD/MM/YYYY
        date_patterns = [
            r'(\d{1,2}[./]\d{1,2}[./]\d{4})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            found_dates.extend(matches)
        
        # Парсимо знайдені дати
        parsed_dates = []
        for date_str in found_dates[:2]:  # Беремо максимум 2 дати
            try:
                # Пробуємо різні формати
                for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        parsed_dates.append(date_obj)
                        break
                    except:
                        continue
            except:
                pass
        
        # Призначаємо дати
        if len(parsed_dates) >= 2:
            dates['start_date'] = min(parsed_dates)
            dates['end_date'] = max(parsed_dates)
        elif len(parsed_dates) == 1:
            # Якщо тільки одна дата, вважаємо її кінцевою
            dates['end_date'] = parsed_dates[0]
        
        return dates
    
    def _extract_terms(self, element) -> str:
        """Витягти умови акції"""
        # Шукаємо секцію з умовами
        terms_keywords = ['умови', 'terms', 'conditions', 'правила', 'rules']
        
        for keyword in terms_keywords:
            terms_elem = element.find(string=re.compile(keyword, re.I))
            if terms_elem and terms_elem.parent:
                parent = terms_elem.parent
                # Піднімаємося вгору для більшого контексту
                for _ in range(2):
                    if parent.parent:
                        parent = parent.parent
                
                text = parent.get_text(strip=True)
                if 20 < len(text) < 1000:
                    return text[:500]
        
        return None
