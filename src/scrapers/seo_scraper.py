"""
SEO Scraper - збір SEO даних сайту конкурента
"""

import time
import logging
import re
import requests
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from ..utils.selenium_helper import SeleniumHelper

logger = logging.getLogger(__name__)


class SEOScraper(SeleniumHelper):
    """Клас для збору SEO даних"""
    
    def scrape(self, url: str) -> Dict[str, Any]:
        """Зібрати всі SEO дані з сайту"""
        logger.info(f"Збір SEO даних з {url}")
        
        seo_data = {
            'title': None,
            'meta_description': None,
            'meta_keywords': None,
            'meta_robots': None,
            'canonical_url': None,
            'og_title': None,
            'og_description': None,
            'og_image': None,
            'og_type': None,
            'h1_tags': [],
            'h2_tags': [],
            'h3_tags': [],
            'robots_txt': None,
            'sitemap_url': None,
            'sitemap_urls_count': 0,
            'structured_data': [],
            'internal_links_count': 0,
            'external_links_count': 0,
            'broken_links_count': 0,
            'page_load_time': None,
            'page_size_kb': None,
        }
        
        try:
            # Запускаємо таймер для page_load_time
            start_time = time.time()
            
            if not self.safe_get(url):
                logger.error(f"Не вдалося завантажити {url}")
                return seo_data
            
            load_time = time.time() - start_time
            seo_data['page_load_time'] = round(load_time, 2)
            
            # Отримуємо HTML
            page_source = self.get_page_source()
            if not page_source:
                logger.error("Порожній HTML-вміст, пропускаємо SEO аналіз")
                return seo_data
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Розмір сторінки
            seo_data['page_size_kb'] = round(len(page_source) / 1024, 2)
            
            # Збираємо мета-теги
            seo_data.update(self._extract_meta_tags(soup))
            
            # Збираємо заголовки
            seo_data.update(self._extract_headings(soup))
            
            # Збираємо структуровані дані
            seo_data['structured_data'] = self._extract_structured_data(soup)
            
            # Аналіз посилань
            links_data = self._analyze_links(soup, url)
            seo_data.update(links_data)
            
            # Отримуємо robots.txt
            seo_data['robots_txt'] = self._get_robots_txt(url)
            
            # Шукаємо sitemap
            sitemap_info = self._find_sitemap(url, seo_data['robots_txt'])
            seo_data['sitemap_url'] = sitemap_info['url']
            seo_data['sitemap_urls_count'] = sitemap_info['urls_count']
            
            logger.info(f"SEO дані успішно зібрано з {url}")
            
        except Exception as e:
            logger.error(f"Помилка збору SEO даних: {e}", exc_info=True)
        
        finally:
            self.close_driver()
        
        return seo_data
    
    def _extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Витягти мета-теги"""
        data = {}
        
        # Title
        title_tag = soup.find('title')
        data['title'] = title_tag.string if title_tag else None
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        data['meta_description'] = meta_desc.get('content') if meta_desc else None
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        data['meta_keywords'] = meta_keywords.get('content') if meta_keywords else None
        
        # Meta robots
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        data['meta_robots'] = meta_robots.get('content') if meta_robots else None
        
        # Canonical URL
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        data['canonical_url'] = canonical.get('href') if canonical else None
        
        # Open Graph tags
        og_title = soup.find('meta', property='og:title')
        data['og_title'] = og_title.get('content') if og_title else None
        
        og_desc = soup.find('meta', property='og:description')
        data['og_description'] = og_desc.get('content') if og_desc else None
        
        og_image = soup.find('meta', property='og:image')
        data['og_image'] = og_image.get('content') if og_image else None
        
        og_type = soup.find('meta', property='og:type')
        data['og_type'] = og_type.get('content') if og_type else None
        
        return data
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Витягти заголовки H1-H3"""
        data = {
            'h1_tags': [],
            'h2_tags': [],
            'h3_tags': [],
        }
        
        # H1
        h1_tags = soup.find_all('h1')
        data['h1_tags'] = [h1.get_text(strip=True) for h1 in h1_tags if h1.get_text(strip=True)]
        
        # H2
        h2_tags = soup.find_all('h2')
        data['h2_tags'] = [h2.get_text(strip=True) for h2 in h2_tags if h2.get_text(strip=True)][:20]  # Обмежуємо до 20
        
        # H3
        h3_tags = soup.find_all('h3')
        data['h3_tags'] = [h3.get_text(strip=True) for h3 in h3_tags if h3.get_text(strip=True)][:20]
        
        return data
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Витягти структуровані дані (JSON-LD, Schema.org)"""
        structured_data = []
        
        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                structured_data.append({
                    'type': 'json-ld',
                    'data': data
                })
            except Exception as e:
                logger.debug(f"Помилка парсингу JSON-LD: {e}")
        
        return structured_data
    
    def _analyze_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, int]:
        """Аналіз посилань на сторінці"""
        data = {
            'internal_links_count': 0,
            'external_links_count': 0,
            'broken_links_count': 0,
        }
        
        base_domain = urlparse(base_url).netloc
        
        all_links = soup.find_all('a', href=True)
        
        internal_links = []
        external_links = []
        
        for link in all_links:
            href = link.get('href', '')
            
            # Пропускаємо якорі та javascript
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Робимо абсолютний URL
            absolute_url = urljoin(base_url, href)
            link_domain = urlparse(absolute_url).netloc
            
            if link_domain == base_domain or not link_domain:
                internal_links.append(absolute_url)
            else:
                external_links.append(absolute_url)
        
        data['internal_links_count'] = len(set(internal_links))
        data['external_links_count'] = len(set(external_links))
        
        return data
    
    def _get_robots_txt(self, url: str) -> str:
        """Отримати вміст robots.txt"""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.debug(f"Не вдалося отримати robots.txt: {e}")
        
        return None
    
    def _find_sitemap(self, url: str, robots_txt: str) -> Dict[str, Any]:
        """Знайти sitemap"""
        sitemap_info = {
            'url': None,
            'urls_count': 0
        }
        
        # Шукаємо в robots.txt
        if robots_txt:
            sitemap_match = re.search(r'Sitemap:\s*(.+)', robots_txt, re.IGNORECASE)
            if sitemap_match:
                sitemap_info['url'] = sitemap_match.group(1).strip()
        
        # Якщо не знайшли, перевіряємо стандартне розташування
        if not sitemap_info['url']:
            parsed = urlparse(url)
            default_sitemap = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
            
            try:
                response = requests.head(default_sitemap, timeout=5)
                if response.status_code == 200:
                    sitemap_info['url'] = default_sitemap
            except:
                pass
        
        # Підраховуємо кількість URL в sitemap
        if sitemap_info['url']:
            try:
                response = requests.get(sitemap_info['url'], timeout=10)
                if response.status_code == 200:
                    # Простий підрахунок URL
                    url_count = response.text.count('<loc>')
                    sitemap_info['urls_count'] = url_count
            except Exception as e:
                logger.debug(f"Помилка підрахунку URL в sitemap: {e}")
        
        return sitemap_info
