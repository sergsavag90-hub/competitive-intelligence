"""
Модуль для обробки robots.txt та дотримання правил обходу сайтів
"""

import logging
import requests
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RobotsParser:
    """Парсер та обробник robots.txt"""
    
    def __init__(self, user_agent: str = "CompetitiveIntelligenceBot/1.0"):
        """
        Ініціалізація парсера
        
        Args:
            user_agent: User-Agent для перевірки правил
        """
        self.user_agent = user_agent
        self._cache = {}  # Кеш robots.txt
        self._cache_timeout = timedelta(hours=24)
    
    def can_fetch(self, url: str) -> bool:
        """
        Перевірити чи можна сканувати URL
        
        Args:
            url: URL для перевірки
            
        Returns:
            True якщо дозволено, False якщо заборонено
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Отримуємо parser для цього домену
            parser = self._get_parser(base_url)
            
            if parser is None:
                # Якщо не вдалось отримати robots.txt, дозволяємо
                logger.warning(f"Не вдалось отримати robots.txt для {base_url}, дозволяємо сканування")
                return True
            
            # Перевіряємо дозвіл
            can_fetch = parser.can_fetch(self.user_agent, url)
            
            if not can_fetch:
                logger.info(f"robots.txt забороняє сканування: {url}")
            
            return can_fetch
            
        except Exception as e:
            logger.error(f"Помилка перевірки robots.txt: {e}")
            # У разі помилки дозволяємо (але логуємо)
            return True
    
    def _get_parser(self, base_url: str) -> Optional[RobotFileParser]:
        """
        Отримати parser для домену (з кешуванням)
        
        Args:
            base_url: Базовий URL сайту
            
        Returns:
            RobotFileParser або None
        """
        # Перевіряємо кеш
        if base_url in self._cache:
            cached_data = self._cache[base_url]
            if datetime.now() - cached_data['timestamp'] < self._cache_timeout:
                return cached_data['parser']
        
        # Завантажуємо robots.txt
        parser = self._fetch_robots(base_url)
        
        # Зберігаємо в кеш
        if parser:
            self._cache[base_url] = {
                'parser': parser,
                'timestamp': datetime.now()
            }
        
        return parser
    
    def _fetch_robots(self, base_url: str) -> Optional[RobotFileParser]:
        """
        Завантажити та розпарсити robots.txt
        
        Args:
            base_url: Базовий URL сайту
            
        Returns:
            RobotFileParser або None
        """
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            
            response = requests.get(
                robots_url,
                timeout=10,
                headers={'User-Agent': self.user_agent}
            )
            
            if response.status_code == 200:
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                logger.info(f"Успішно завантажено robots.txt з {base_url}")
                return parser
            else:
                logger.info(f"robots.txt не знайдено на {base_url} (статус: {response.status_code})")
                return None
                
        except requests.RequestException as e:
            logger.warning(f"Не вдалось завантажити robots.txt з {base_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Помилка обробки robots.txt: {e}")
            return None
    
    def get_crawl_delay(self, base_url: str) -> Optional[float]:
        """
        Отримати рекомендовану затримку між запитами
        
        Args:
            base_url: Базовий URL сайту
            
        Returns:
            Затримка в секундах або None
        """
        try:
            parser = self._get_parser(base_url)
            
            if parser is None:
                return None
            
            # Отримуємо crawl-delay для нашого user-agent
            delay = parser.crawl_delay(self.user_agent)
            
            if delay:
                logger.info(f"Crawl-delay для {base_url}: {delay}с")
                return float(delay)
            
            return None
            
        except Exception as e:
            logger.error(f"Помилка отримання crawl-delay: {e}")
            return None
    
    def get_sitemaps(self, base_url: str) -> List[str]:
        """
        Отримати список URL sitemap з robots.txt
        
        Args:
            base_url: Базовий URL сайту
            
        Returns:
            Список URL sitemap
        """
        try:
            parser = self._get_parser(base_url)
            
            if parser is None:
                return []
            
            # RobotFileParser не має прямого методу для sitemap,
            # тому парсимо вручну
            robots_url = urljoin(base_url, '/robots.txt')
            response = requests.get(
                robots_url,
                timeout=10,
                headers={'User-Agent': self.user_agent}
            )
            
            if response.status_code != 200:
                return []
            
            sitemaps = []
            for line in response.text.splitlines():
                line = line.strip()
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    sitemaps.append(sitemap_url)
            
            logger.info(f"Знайдено {len(sitemaps)} sitemap в robots.txt")
            return sitemaps
            
        except Exception as e:
            logger.error(f"Помилка отримання sitemap: {e}")
            return []
    
    def get_robots_info(self, base_url: str) -> Dict[str, Any]:
        """
        Отримати повну інформацію з robots.txt
        
        Args:
            base_url: Базовий URL сайту
            
        Returns:
            Словник з інформацією
        """
        try:
            parser = self._get_parser(base_url)
            
            info = {
                'base_url': base_url,
                'robots_url': urljoin(base_url, '/robots.txt'),
                'crawl_delay': self.get_crawl_delay(base_url),
                'sitemaps': self.get_sitemaps(base_url),
                'disallowed_paths': [],
                'allowed_paths': [],
                'retrieved_at': datetime.now().isoformat()
            }
            
            if parser is None:
                info['error'] = 'Could not fetch robots.txt'
                return info
            
            # Отримуємо заборонені шляхи
            # Примітка: RobotFileParser не надає прямого доступу до правил,
            # тому парсимо вручну
            robots_url = urljoin(base_url, '/robots.txt')
            response = requests.get(
                robots_url,
                timeout=10,
                headers={'User-Agent': self.user_agent}
            )
            
            if response.status_code == 200:
                current_agent = None
                for line in response.text.splitlines():
                    line = line.strip()
                    
                    if line.lower().startswith('user-agent:'):
                        current_agent = line.split(':', 1)[1].strip()
                    
                    # Перевіряємо чи це стосується нашого агента
                    if current_agent in ['*', self.user_agent]:
                        if line.lower().startswith('disallow:'):
                            path = line.split(':', 1)[1].strip()
                            if path and path not in info['disallowed_paths']:
                                info['disallowed_paths'].append(path)
                        
                        elif line.lower().startswith('allow:'):
                            path = line.split(':', 1)[1].strip()
                            if path and path not in info['allowed_paths']:
                                info['allowed_paths'].append(path)
            
            return info
            
        except Exception as e:
            logger.error(f"Помилка отримання інформації robots.txt: {e}")
            return {
                'base_url': base_url,
                'error': str(e)
            }
    
    def respect_meta_robots(self, html_content: str) -> Dict[str, bool]:
        """
        Перевірити meta robots теги в HTML
        
        Args:
            html_content: HTML контент сторінки
            
        Returns:
            Словник з правилами (noindex, nofollow, etc.)
        """
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Шукаємо meta robots теги
            meta_robots = soup.find_all('meta', attrs={'name': 'robots'})
            
            rules = {
                'noindex': False,
                'nofollow': False,
                'noarchive': False,
                'nosnippet': False,
                'noimageindex': False
            }
            
            for meta in meta_robots:
                content = meta.get('content', '').lower()
                
                if 'noindex' in content:
                    rules['noindex'] = True
                if 'nofollow' in content:
                    rules['nofollow'] = True
                if 'noarchive' in content:
                    rules['noarchive'] = True
                if 'nosnippet' in content:
                    rules['nosnippet'] = True
                if 'noimageindex' in content:
                    rules['noimageindex'] = True
            
            if any(rules.values()):
                logger.info(f"Виявлено meta robots обмеження: {rules}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Помилка обробки meta robots: {e}")
            return {
                'noindex': False,
                'nofollow': False,
                'noarchive': False,
                'nosnippet': False,
                'noimageindex': False
            }


class SmartCrawler:
    """Розумний краулер з дотриманням robots.txt"""
    
    def __init__(self, user_agent: str = "CompetitiveIntelligenceBot/1.0"):
        """
        Ініціалізація краулера
        
        Args:
            user_agent: User-Agent
        """
        self.robots_parser = RobotsParser(user_agent)
        self.user_agent = user_agent
        self.default_delay = 1.0  # Секунди між запитами за замовчуванням
    
    def should_crawl(self, url: str, html_content: str = None) -> bool:
        """
        Визначити чи можна сканувати URL
        
        Args:
            url: URL для перевірки
            html_content: HTML контент (опціонально, для перевірки meta tags)
            
        Returns:
            True якщо можна сканувати
        """
        # Перевіряємо robots.txt
        if not self.robots_parser.can_fetch(url):
            return False
        
        # Перевіряємо meta robots теги
        if html_content:
            meta_rules = self.robots_parser.respect_meta_robots(html_content)
            if meta_rules['noindex']:
                logger.info(f"Сторінка має noindex meta tag: {url}")
                return False
        
        return True
    
    def get_crawl_delay(self, url: str) -> float:
        """
        Отримати рекомендовану затримку для URL
        
        Args:
            url: URL сайту
            
        Returns:
            Затримка в секундах
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        delay = self.robots_parser.get_crawl_delay(base_url)
        
        return delay if delay is not None else self.default_delay
