"""
SEO Intelligence Module

This module provides functionality to extract and analyze SEO-related information from websites,
including meta tags, keywords, robots.txt, sitemap, and page structure analysis.

Author: sergsavag90-hub
Date: 2025-12-12
"""

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Dict, List, Optional, Tuple
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SEOIntelligence:
    """
    A comprehensive SEO intelligence analyzer for competitive intelligence gathering.
    
    This class provides methods to extract and analyze:
    - Meta tags (title, description, keywords, OG tags, canonical, etc.)
    - Keywords and keyword density
    - robots.txt directives
    - Sitemap structure and URLs
    - Page structure (headings, links, images, schema markup, etc.)
    """
    
    def __init__(self, timeout: int = 10, user_agent: Optional[str] = None):
        """
        Initialize the SEO Intelligence analyzer.
        
        Args:
            timeout: Request timeout in seconds (default: 10)
            user_agent: Custom user agent string (default: standard browser user agent)
        """
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        self.headers = {"User-Agent": self.user_agent}
    
    def get_base_url(self, url: str) -> str:
        """Extract the base URL from a given URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def fetch_page(self, url: str) -> Optional[requests.Response]:
        """
        Fetch a web page with error handling.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response object or None if request fails
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def extract_meta_tags(self, url: str) -> Dict:
        """
        Extract meta tags from a webpage.
        
        Args:
            url: URL of the webpage
            
        Returns:
            Dictionary containing extracted meta information
        """
        response = self.fetch_page(url)
        if not response:
            return {}
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            meta_info = {}
            
            # Basic meta tags
            meta_info['title'] = soup.title.string if soup.title else None
            meta_info['meta_description'] = self._get_meta_content(soup, 'name', 'description')
            meta_info['meta_keywords'] = self._get_meta_content(soup, 'name', 'keywords')
            meta_info['charset'] = self._get_meta_charset(soup)
            meta_info['viewport'] = self._get_meta_content(soup, 'name', 'viewport')
            meta_info['robots'] = self._get_meta_content(soup, 'name', 'robots')
            
            # Open Graph tags
            meta_info['og_title'] = self._get_meta_content(soup, 'property', 'og:title')
            meta_info['og_description'] = self._get_meta_content(soup, 'property', 'og:description')
            meta_info['og_image'] = self._get_meta_content(soup, 'property', 'og:image')
            meta_info['og_url'] = self._get_meta_content(soup, 'property', 'og:url')
            meta_info['og_type'] = self._get_meta_content(soup, 'property', 'og:type')
            
            # Twitter Card tags
            meta_info['twitter_card'] = self._get_meta_content(soup, 'name', 'twitter:card')
            meta_info['twitter_title'] = self._get_meta_content(soup, 'name', 'twitter:title')
            meta_info['twitter_description'] = self._get_meta_content(soup, 'name', 'twitter:description')
            meta_info['twitter_image'] = self._get_meta_content(soup, 'name', 'twitter:image')
            
            # Canonical and alternate links
            meta_info['canonical'] = self._get_link_href(soup, 'canonical')
            meta_info['alternate_langs'] = self._get_alternate_languages(soup)
            
            # Additional meta tags
            meta_info['language'] = self._get_meta_content(soup, 'http-equiv', 'Content-Language')
            meta_info['author'] = self._get_meta_content(soup, 'name', 'author')
            meta_info['theme_color'] = self._get_meta_content(soup, 'name', 'theme-color')
            
            return meta_info
        
        except Exception as e:
            logger.error(f"Error extracting meta tags from {url}: {e}")
            return {}
    
    def _get_meta_content(self, soup: BeautifulSoup, attr_name: str, attr_value: str) -> Optional[str]:
        """Helper method to get meta tag content."""
        meta_tag = soup.find('meta', {attr_name: attr_value})
        return meta_tag.get('content') if meta_tag else None
    
    def _get_meta_charset(self, soup: BeautifulSoup) -> Optional[str]:
        """Helper method to get charset from meta tag."""
        meta_charset = soup.find('meta', charset=True)
        return meta_charset.get('charset') if meta_charset else None
    
    def _get_link_href(self, soup: BeautifulSoup, rel: str) -> Optional[str]:
        """Helper method to get href from link tag."""
        link = soup.find('link', {'rel': rel})
        return link.get('href') if link else None
    
    def _get_alternate_languages(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Helper method to get alternate language links."""
        alternate_langs = []
        for link in soup.find_all('link', {'rel': 'alternate'}):
            hreflang = link.get('hreflang')
            href = link.get('href')
            if hreflang and href:
                alternate_langs.append({'lang': hreflang, 'url': href})
        return alternate_langs
    
    def extract_keywords(self, url: str, top_n: int = 20, min_length: int = 3) -> Dict:
        """
        Extract and analyze keywords from page content.
        
        Args:
            url: URL of the webpage
            top_n: Number of top keywords to return (default: 20)
            min_length: Minimum word length to consider (default: 3)
            
        Returns:
            Dictionary containing keyword analysis
        """
        response = self.fetch_page(url)
        if not response:
            return {}
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean and tokenize
            words = re.findall(r'\b[a-z]+\b', text.lower())
            
            # Filter words
            stop_words = self._get_common_stop_words()
            filtered_words = [
                word for word in words 
                if len(word) >= min_length and word not in stop_words
            ]
            
            # Calculate keyword frequency
            word_freq = Counter(filtered_words)
            top_keywords = word_freq.most_common(top_n)
            
            # Calculate keyword density for top keywords
            total_words = len(filtered_words)
            keyword_density = {}
            for keyword, count in top_keywords:
                density = (count / total_words * 100) if total_words > 0 else 0
                keyword_density[keyword] = {
                    'count': count,
                    'density': round(density, 2)
                }
            
            return {
                'total_words': total_words,
                'unique_words': len(word_freq),
                'keywords': keyword_density,
                'top_keywords': [kw for kw, _ in top_keywords]
            }
        
        except Exception as e:
            logger.error(f"Error extracting keywords from {url}: {e}")
            return {}
    
    def _get_common_stop_words(self) -> set:
        """Return a set of common English stop words."""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'that', 'this', 'these',
            'those', 'which', 'who', 'whom', 'what', 'when', 'where', 'why', 'how'
        }
    
    def extract_robots_txt(self, url: str) -> Dict:
        """
        Extract and parse robots.txt file.
        
        Args:
            url: Base URL of the website
            
        Returns:
            Dictionary containing robots.txt directives
        """
        base_url = self.get_base_url(url)
        robots_url = urljoin(base_url, '/robots.txt')
        
        response = self.fetch_page(robots_url)
        if not response:
            return {'exists': False, 'content': None}
        
        try:
            content = response.text
            rules = self._parse_robots_txt(content)
            
            return {
                'exists': True,
                'url': robots_url,
                'content': content,
                'rules': rules,
                'sitemaps': self._extract_sitemaps_from_robots(content)
            }
        
        except Exception as e:
            logger.error(f"Error parsing robots.txt from {base_url}: {e}")
            return {'exists': True, 'error': str(e)}
    
    def _parse_robots_txt(self, content: str) -> List[Dict]:
        """Parse robots.txt content into structured rules."""
        rules = []
        current_user_agent = None
        
        for line in content.split('\n'):
            line = line.strip().split('#')[0].strip()
            if not line:
                continue
            
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == 'user-agent':
                current_user_agent = value
                rules.append({
                    'user_agent': value,
                    'disallows': [],
                    'allows': [],
                    'crawl_delay': None
                })
            elif key == 'disallow' and current_user_agent:
                if rules and rules[-1]['user_agent'] == current_user_agent:
                    rules[-1]['disallows'].append(value)
            elif key == 'allow' and current_user_agent:
                if rules and rules[-1]['user_agent'] == current_user_agent:
                    rules[-1]['allows'].append(value)
            elif key == 'crawl-delay' and current_user_agent:
                if rules and rules[-1]['user_agent'] == current_user_agent:
                    rules[-1]['crawl_delay'] = value
        
        return rules
    
    def _extract_sitemaps_from_robots(self, content: str) -> List[str]:
        """Extract sitemap URLs from robots.txt content."""
        sitemaps = []
        for line in content.split('\n'):
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                sitemaps.append(sitemap_url)
        return sitemaps
    
    def extract_sitemap(self, url: str) -> Dict:
        """
        Extract and parse sitemap.xml file.
        
        Args:
            url: Base URL of the website or direct sitemap URL
            
        Returns:
            Dictionary containing sitemap information
        """
        base_url = self.get_base_url(url)
        
        # Try common sitemap locations
        sitemap_urls = [
            url if 'sitemap' in url else urljoin(base_url, '/sitemap.xml'),
            urljoin(base_url, '/sitemap_index.xml'),
        ]
        
        for sitemap_url in sitemap_urls:
            response = self.fetch_page(sitemap_url)
            if response:
                try:
                    urls = self._parse_sitemap(response.content)
                    return {
                        'exists': True,
                        'url': sitemap_url,
                        'total_urls': len(urls),
                        'urls': urls
                    }
                except Exception as e:
                    logger.debug(f"Failed to parse {sitemap_url}: {e}")
                    continue
        
        return {'exists': False, 'message': 'Sitemap not found'}
    
    def _parse_sitemap(self, content: bytes) -> List[Dict]:
        """Parse sitemap XML content."""
        urls = []
        try:
            root = ET.fromstring(content)
            
            # Extract namespace
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Find all URL entries
            for url_elem in root.findall('.//ns:url', namespace):
                url_data = {}
                
                loc = url_elem.find('ns:loc', namespace)
                lastmod = url_elem.find('ns:lastmod', namespace)
                changefreq = url_elem.find('ns:changefreq', namespace)
                priority = url_elem.find('ns:priority', namespace)
                
                if loc is not None:
                    url_data['loc'] = loc.text
                    url_data['lastmod'] = lastmod.text if lastmod is not None else None
                    url_data['changefreq'] = changefreq.text if changefreq is not None else None
                    url_data['priority'] = priority.text if priority is not None else None
                    urls.append(url_data)
        
        except Exception as e:
            logger.error(f"Error parsing sitemap XML: {e}")
        
        return urls
    
    def extract_page_structure(self, url: str) -> Dict:
        """
        Extract and analyze page structure information.
        
        Args:
            url: URL of the webpage
            
        Returns:
            Dictionary containing page structure analysis
        """
        response = self.fetch_page(url)
        if not response:
            return {}
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            structure = {
                'headings': self._extract_headings(soup),
                'links': self._extract_links(soup, url),
                'images': self._extract_images(soup, url),
                'schema_markup': self._extract_schema_markup(soup),
                'lists': self._extract_lists(soup),
                'tables': self._extract_tables(soup),
                'forms': self._extract_forms(soup),
                'iframes': len(soup.find_all('iframe')),
                'word_count': self._count_words(soup),
                'language': soup.html.get('lang') if soup.html else None,
                'h1_count': len(soup.find_all('h1')),
                'h2_count': len(soup.find_all('h2')),
                'paragraphs_count': len(soup.find_all('p')),
            }
            
            return structure
        
        except Exception as e:
            logger.error(f"Error extracting page structure from {url}: {e}")
            return {}
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract all headings from the page."""
        headings = {}
        for i in range(1, 7):
            tag = f'h{i}'
            h_tags = soup.find_all(tag)
            headings[tag] = [h.get_text().strip() for h in h_tags]
        return headings
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Extract and categorize links from the page."""
        internal_links = []
        external_links = []
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().strip()
            
            if not href or href.startswith('#'):
                continue
            
            link_data = {'url': href, 'text': text}
            
            # Determine if internal or external
            if href.startswith('http'):
                link_domain = urlparse(href).netloc
                if link_domain == base_domain:
                    internal_links.append(link_data)
                else:
                    external_links.append(link_data)
            else:
                internal_links.append(link_data)
        
        return {
            'total_links': len(internal_links) + len(external_links),
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'internal_links_list': internal_links,
            'external_links_list': external_links
        }
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Extract and analyze images from the page."""
        images = []
        images_without_alt = 0
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '').strip()
            title = img.get('title', '').strip()
            
            if not alt:
                images_without_alt += 1
            
            images.append({
                'src': urljoin(base_url, src) if src and not src.startswith('http') else src,
                'alt': alt,
                'title': title
            })
        
        return {
            'total_images': len(images),
            'images_without_alt': images_without_alt,
            'images': images
        }
    
    def _extract_schema_markup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON-LD schema markup from the page."""
        schema_data = []
        
        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            try:
                import json
                data = json.loads(script.string)
                schema_data.append(data)
            except Exception as e:
                logger.debug(f"Error parsing schema markup: {e}")
        
        return schema_data
    
    def _extract_lists(self, soup: BeautifulSoup) -> Dict:
        """Extract list information from the page."""
        return {
            'ordered_lists': len(soup.find_all('ol')),
            'unordered_lists': len(soup.find_all('ul')),
            'description_lists': len(soup.find_all('dl'))
        }
    
    def _extract_tables(self, soup: BeautifulSoup) -> Dict:
        """Extract table information from the page."""
        tables = []
        
        for table in soup.find_all('table'):
            rows = len(table.find_all('tr'))
            cols = max(len(row.find_all(['td', 'th'])) for row in table.find_all('tr')) if rows > 0 else 0
            caption = table.find('caption')
            
            tables.append({
                'rows': rows,
                'columns': cols,
                'caption': caption.get_text().strip() if caption else None
            })
        
        return {
            'total_tables': len(tables),
            'tables': tables
        }
    
    def _extract_forms(self, soup: BeautifulSoup) -> Dict:
        """Extract form information from the page."""
        forms = []
        
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET').upper(),
                'input_fields': len(form.find_all('input')),
                'textarea_fields': len(form.find_all('textarea')),
                'select_fields': len(form.find_all('select')),
                'buttons': len(form.find_all('button'))
            }
            forms.append(form_data)
        
        return {
            'total_forms': len(forms),
            'forms': forms
        }
    
    def _count_words(self, soup: BeautifulSoup) -> int:
        """Count total words in the page content."""
        for script in soup(['script', 'style']):
            script.decompose()
        
        text = soup.get_text()
        words = text.split()
        return len(words)
    
    def full_seo_analysis(self, url: str) -> Dict:
        """
        Perform a complete SEO analysis of a webpage.
        
        Args:
            url: URL of the webpage to analyze
            
        Returns:
            Dictionary containing comprehensive SEO analysis results
        """
        logger.info(f"Starting full SEO analysis for {url}")
        
        analysis = {
            'url': url,
            'timestamp': self._get_timestamp(),
            'meta_tags': self.extract_meta_tags(url),
            'keywords': self.extract_keywords(url),
            'page_structure': self.extract_page_structure(url),
            'robots_txt': self.extract_robots_txt(url),
            'sitemap': self.extract_sitemap(url)
        }
        
        logger.info(f"SEO analysis completed for {url}")
        return analysis
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


# Example usage
if __name__ == "__main__":
    # Initialize the SEO Intelligence analyzer
    seo = SEOIntelligence()
    
    # Example: Analyze a website
    test_url = "https://www.example.com"
    print(f"Analyzing: {test_url}")
    
    # Extract meta tags
    meta = seo.extract_meta_tags(test_url)
    print("\nMeta Tags:")
    print(meta)
    
    # Extract keywords
    keywords = seo.extract_keywords(test_url)
    print("\nKeywords:")
    print(keywords)
    
    # Extract robots.txt
    robots = seo.extract_robots_txt(test_url)
    print("\nRobots.txt:")
    print(robots)
    
    # Extract sitemap
    sitemap = seo.extract_sitemap(test_url)
    print("\nSitemap:")
    print(sitemap)
    
    # Extract page structure
    structure = seo.extract_page_structure(test_url)
    print("\nPage Structure:")
    print(structure)
    
    # Perform full analysis
    full_analysis = seo.full_seo_analysis(test_url)
    print("\nFull SEO Analysis:")
    print(full_analysis)
