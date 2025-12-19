"""
Site Crawler - утиліта для обходу сайту та збору посилань
"""

import logging
from typing import Set, List, Optional, Callable, Any, Dict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from requests import Session, RequestException

from .config import config
from .selenium_helper import SeleniumHelper

logger = logging.getLogger(__name__)


class SiteCrawler:
    """
    Клас для обходу сайту, збору посилань та виконання функції
    на кожній знайденій сторінці.
    """

    def __init__(self, base_url: str, max_pages: int = 50, max_depth: int = 3):
        self.base_url = self._normalize_url(base_url)
        self.base_domain = urlparse(self.base_url).netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.visited_urls: Set[str] = set()
        self.urls_to_visit: List[Dict[str, Any]] = [{'url': self.base_url, 'depth': 0}]
        self.results: List[Any] = []
        self.selenium_helper = SeleniumHelper()
        self.session = Session()
        self.session.headers.update({'User-Agent': config.user_agent})
        logger.info(f"SiteCrawler ініціалізовано для {self.base_domain}")

    def _normalize_url(self, url: str) -> str:
        """Нормалізує URL, видаляючи фрагменти та параметри запиту."""
        parsed = urlparse(url)
        return parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip('/')

    def _is_internal(self, url: str) -> bool:
        """Перевіряє, чи є посилання внутрішнім."""
        return urlparse(url).netloc == self.base_domain

    def _is_crawlable(self, url: str) -> bool:
        """Перевіряє, чи можна обходити посилання."""
        if not self._is_internal(url):
            return False
        
        # Ігноруємо посилання на файли
        if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.rar', '.mp4', '.mp3']):
            return False
        
        # Ігноруємо посилання з фрагментами (якорями)
        if '#' in url:
            return False
            
        return True

    def _extract_links(self, html_content: str, current_url: str) -> Set[str]:
        """Витягує внутрішні посилання зі сторінки."""
        links: Set[str] = set()
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Робимо абсолютний URL
                absolute_url = urljoin(current_url, href)
                normalized_url = self._normalize_url(absolute_url)
                
                if self._is_crawlable(normalized_url):
                    links.add(normalized_url)
        except Exception as e:
            logger.error(f"Помилка вилучення посилань з {current_url}: {e}")
            
        return links

    def crawl(self, process_page_func: Callable[[str, str], Any]) -> List[Any]:
        """
        Запускає обхід сайту.
        
        Args:
            process_page_func: Функція, яка буде викликана для кожної сторінки.
                               Приймає (url: str, html_content: str) і повертає результат.
        
        Returns:
            Список результатів, повернутих process_page_func.
        """
        
        while self.urls_to_visit and len(self.visited_urls) < self.max_pages:
            current_item = self.urls_to_visit.pop(0)
            current_url = current_item['url']
            current_depth = current_item['depth']

            if current_url in self.visited_urls:
                continue

            self.visited_urls.add(current_url)
            logger.info(f"Обхід сторінки ({len(self.visited_urls)}/{self.max_pages}, глибина {current_depth}): {current_url}")

            html_content: Optional[str] = None
            
            # Використовуємо requests для швидкого отримання HTML, якщо не потрібен JS
            try:
                response = self.session.get(current_url, timeout=config.request_timeout)
                response.raise_for_status()
                html_content = response.text
            except RequestException as e:
                logger.warning(f"Помилка HTTP-запиту для {current_url}: {e}. Пропускаємо.")
                continue
            except Exception as e:
                logger.error(f"Неочікувана помилка при отриманні {current_url}: {e}")
                continue

            # 1. Обробка сторінки
            try:
                result = process_page_func(current_url, html_content)
                if result:
                    self.results.append(result)
            except Exception as e:
                logger.error(f"Помилка обробки сторінки {current_url}: {e}")

            # 2. Вилучення нових посилань
            if current_depth < self.max_depth:
                new_links = self._extract_links(html_content, current_url)
                
                for link in new_links:
                    if link not in self.visited_urls and link not in [item['url'] for item in self.urls_to_visit]:
                        self.urls_to_visit.append({'url': link, 'depth': current_depth + 1})
                        
        logger.info(f"Обхід завершено. Відвідано {len(self.visited_urls)} сторінок.")
        return self.results
