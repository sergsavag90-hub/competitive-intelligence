"""
Site Crawler - інтелігентний обхід сайту з адаптивним аналізом пагінації
"""

import logging
import time
import requests
import re
from typing import Dict, Any, List, Set, Callable, Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from collections import deque

logger = logging.getLogger(__name__)


class PaginationDetector:
    """Детектор пагінації для різних типів сайтів"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.detected_patterns = []
        
    def detect_pagination(self, soup: BeautifulSoup, current_url: str) -> Optional[Dict[str, Any]]:
        """
        Визначає структуру пагінації на сторінці
        
        Returns:
            Dict з інформацією про пагінацію або None якщо не знайдено
        """
        # Метод 1: Пошук посилань з числами (1, 2, 3, Next, тощо)
        pagination_links = self._find_pagination_links(soup, current_url)
        if pagination_links:
            pattern = self._analyze_pagination_pattern(pagination_links)
            if pattern:
                return {
                    'type': 'link_based',
                    'pattern': pattern,
                    'links': pagination_links[:10]  # Перші 10 для аналізу
                }
        
        # Метод 2: Query parameters (page=N, p=N, start=N)
        query_param_pattern = self._detect_query_param_pagination(current_url)
        if query_param_pattern:
            return {
                'type': 'query_param',
                'pattern': query_param_pattern
            }
        
        # Метод 3: Path-based (/page/2/, /2/, тощо)
        path_pattern = self._detect_path_pagination(current_url)
        if path_pattern:
            return {
                'type': 'path_based',
                'pattern': path_pattern
            }
        
        return None
    
    def _find_pagination_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Знаходить посилання, які схожі на пагінацію"""
        pagination_keywords = [
            'next', 'prev', 'previous', 'page', 'pagination', 
            'pager', 'наступна', 'попередня', 'сторінка'
        ]
        
        potential_links = []
        
        # Шукаємо посилання з числами
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Перевіряємо чи містить число або ключові слова
            if (re.search(r'\d+', href) or re.search(r'\d+', text) or 
                any(keyword in text for keyword in pagination_keywords) or
                any(keyword in href.lower() for keyword in pagination_keywords)):
                
                absolute_url = urljoin(current_url, href)
                # Перевіряємо що це той самий домен
                if urlparse(absolute_url).netloc == urlparse(current_url).netloc:
                    potential_links.append(absolute_url)
        
        return potential_links
    
    def _analyze_pagination_pattern(self, links: List[str]) -> Optional[Dict[str, Any]]:
        """Аналізує структуру пагінації з посилань"""
        if not links:
            return None
        
        # Перевіряємо query parameters
        query_params = []
        for link in links:
            parsed = urlparse(link)
            params = parse_qs(parsed.query)
            if params:
                query_params.append(params)
        
        if query_params:
            # Шукаємо спільний параметр з числом
            common_param = self._find_common_numeric_param(query_params)
            if common_param:
                return {
                    'method': 'query_param',
                    'param_name': common_param
                }
        
        # Перевіряємо шлях (path)
        paths = [urlparse(link).path for link in links]
        path_pattern = self._find_common_path_pattern(paths)
        if path_pattern:
            return {
                'method': 'path',
                'pattern': path_pattern
            }
        
        return None
    
    def _find_common_numeric_param(self, param_lists: List[Dict]) -> Optional[str]:
        """Знаходить спільний параметр з числовим значенням"""
        param_counts = {}
        
        for params in param_lists:
            for key, values in params.items():
                # Перевіряємо чи є числа в значеннях
                if any(re.match(r'^\d+$', str(v)) for v in values):
                    param_counts[key] = param_counts.get(key, 0) + 1
        
        if param_counts:
            # Повертаємо найпопулярніший параметр
            return max(param_counts, key=param_counts.get)
        
        return None
    
    def _find_common_path_pattern(self, paths: List[str]) -> Optional[str]:
        """Знаходить спільний паттерн у шляхах"""
        if not paths:
            return None
        
        # Перевіряємо паттерни типу /page/N/
        page_pattern = re.compile(r'/page/(\d+)/?')
        if all(page_pattern.search(path) for path in paths):
            return '/page/{N}/'
        
        # Перевіряємо паттерни типу /N/
        simple_pattern = re.compile(r'/(\d+)/?$')
        if all(simple_pattern.search(path) for path in paths):
            return '/{N}/'
        
        return None
    
    def _detect_query_param_pagination(self, url: str) -> Optional[Dict[str, Any]]:
        """Визначає пагінацію через query parameters"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Список можливих параметрів пагінації
        pagination_params = ['page', 'p', 'pg', 'start', 'offset', 'from']
        
        for param in pagination_params:
            if param in params:
                try:
                    value = int(params[param][0])
                    return {
                        'param_name': param,
                        'current_value': value
                    }
                except ValueError:
                    continue
        
        return None
    
    def _detect_path_pagination(self, url: str) -> Optional[Dict[str, Any]]:
        """Визначає пагінацію через шлях URL"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Паттерн /page/N/
        page_match = re.search(r'/page/(\d+)/?', path)
        if page_match:
            return {
                'pattern': '/page/{N}/',
                'current_page': int(page_match.group(1))
            }
        
        # Паттерн /N/ в кінці
        simple_match = re.search(r'/(\d+)/?$', path)
        if simple_match:
            return {
                'pattern': '/{N}/',
                'current_page': int(simple_match.group(1))
            }
        
        return None
    
    def generate_next_page_url(self, current_url: str, pagination_info: Dict[str, Any], page_num: int) -> str:
        """Генерує URL наступної сторінки на основі виявленої структури"""
        if pagination_info['type'] == 'query_param':
            pattern = pagination_info['pattern']
            parsed = urlparse(current_url)
            params = parse_qs(parsed.query)
            params[pattern['param_name']] = [str(page_num)]
            
            new_query = urlencode(params, doseq=True)
            return urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))
        
        elif pagination_info['type'] == 'path_based':
            pattern = pagination_info['pattern']['pattern']
            parsed = urlparse(current_url)
            
            if '/page/{N}/' in pattern:
                new_path = re.sub(r'/page/\d+/?', f'/page/{page_num}/', parsed.path)
            elif '/{N}/' in pattern:
                new_path = re.sub(r'/\d+/?$', f'/{page_num}/', parsed.path)
            else:
                new_path = parsed.path
            
            return urlunparse((
                parsed.scheme, parsed.netloc, new_path,
                parsed.params, parsed.query, parsed.fragment
            ))
        
        return current_url


class SiteCrawler:
    """
    Інтелігентний краулер для обходу сайту з автоматичним розпізнаванням пагінації
    """
    
    def __init__(self, base_url: str, max_pages: int = 50, max_depth: int = 3, 
                 respect_robots: bool = True, delay: float = 0.5):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.respect_robots = respect_robots
        self.delay = delay
        
        self.visited: Set[str] = set()
        self.to_visit: deque = deque([(base_url, 0)])  # (url, depth)
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        self.pagination_detector = PaginationDetector(base_url)
        self.pagination_pattern = None
        self.needs_help = False
        self.help_message = None
        
    def crawl(self, process_func: Callable[[str, str], Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Обходить сайт і застосовує функцію обробки до кожної сторінки
        
        Args:
            process_func: Функція, яка приймає (url, html_content) і повертає Dict з даними
        
        Returns:
            Список результатів обробки кожної сторінки
        """
        results = []
        
        logger.info(f"Початок обходу сайту {self.base_url}")
        logger.info(f"Максимум сторінок: {self.max_pages}, Максимальна глибина: {self.max_depth}")
        
        while self.to_visit and len(self.visited) < self.max_pages:
            url, depth = self.to_visit.popleft()
            
            # Перевіряємо глибину
            if depth > self.max_depth:
                continue
            
            # Перевіряємо чи не відвідували раніше
            if url in self.visited:
                continue
            
            # Додаємо затримку між запитами
            if self.visited:  # Не затримуємо перший запит
                time.sleep(self.delay)
            
            try:
                # Завантажуємо сторінку
                logger.info(f"Обробка сторінки ({len(self.visited) + 1}/{self.max_pages}): {url}")
                html_content = self._fetch_page(url)
                
                if not html_content:
                    continue
                
                # Відмічаємо як відвідану
                self.visited.add(url)
                
                # Обробляємо сторінку
                page_data = process_func(url, html_content)
                results.append(page_data)
                
                # Парсимо для знаходження нових посилань
                soup = BeautifulSoup(html_content, 'lxml')
                
                # Виявляємо пагінацію (тільки на першій сторінці)
                if len(self.visited) == 1:
                    self.pagination_pattern = self.pagination_detector.detect_pagination(soup, url)
                    if self.pagination_pattern:
                        logger.info(f"Виявлено пагінацію: {self.pagination_pattern['type']}")
                    else:
                        logger.warning("Пагінація не виявлена автоматично")
                        # Тут можна запитати користувача
                        self.needs_help = True
                        self.help_message = (
                            f"Не вдалося автоматично визначити структуру пагінації для {url}. "
                            "Будь ласка, вкажіть приклади URL сторінок пагінації."
                        )
                
                # Додаємо нові посилання до черги
                new_links = self._extract_links(soup, url, depth)
                for link in new_links:
                    if link not in self.visited and (link, depth + 1) not in self.to_visit:
                        self.to_visit.append((link, depth + 1))
                
            except Exception as e:
                logger.error(f"Помилка обробки {url}: {e}", exc_info=True)
                continue
        
        logger.info(f"Обхід завершено. Оброблено {len(results)} сторінок.")
        return results
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """Завантажує HTML сторінки"""
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Помилка завантаження {url}: {e}")
            return None
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str, current_depth: int) -> List[str]:
        """Витягує посилання зі сторінки"""
        links = set()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            # Пропускаємо якорі, javascript, mailto
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            # Робимо абсолютний URL
            absolute_url = urljoin(base_url, href)
            
            # Перевіряємо що це той самий домен
            if urlparse(absolute_url).netloc != self.domain:
                continue
            
            # Видаляємо фрагменти
            parsed = urlparse(absolute_url)
            clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                                   parsed.params, parsed.query, ''))
            
            links.add(clean_url)
        
        return list(links)
    
    def set_pagination_pattern(self, pattern: str):
        """Встановлює паттерн пагінації вручну (з допомоги користувача)"""
        # Аналізуємо надані приклади
        examples = [url.strip() for url in pattern.split(',') if url.strip()]
        
        if examples:
            # Намагаємося визначити паттерн з прикладів
            self.pagination_pattern = self._analyze_user_pagination_examples(examples)
            self.needs_help = False
            logger.info(f"Встановлено паттерн пагінації з допомоги користувача: {self.pagination_pattern}")
    
    def _analyze_user_pagination_examples(self, examples: List[str]) -> Dict[str, Any]:
        """Аналізує приклади URL пагінації від користувача"""
        # Додаємо їх до черги для обробки
        for url in examples:
            if url not in self.visited:
                self.to_visit.append((url, 1))
        
        # Повертаємо базовий паттерн
        return {
            'type': 'user_provided',
            'examples': examples
        }
