"""
Company Data Scraper - збір контактної інформації компанії
"""

import logging
import re
from typing import Dict, Any, List, Set, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import phonenumbers
from phonenumbers import PhoneNumberMatcher, PhoneNumberFormat, NumberParseException

from ..utils.selenium_helper import SeleniumHelper

logger = logging.getLogger(__name__)


class CompanyScraper(SeleniumHelper):
    """Клас для збору контактних даних компанії"""
    
    # Регулярні вирази для пошуку
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    # Social media домени
    SOCIAL_MEDIA = {
        'facebook': ['facebook.com', 'fb.com'],
        'instagram': ['instagram.com'],
        'linkedin': ['linkedin.com'],
        'twitter': ['twitter.com', 'x.com'],
        'youtube': ['youtube.com', 'youtu.be'],
        'telegram': ['t.me', 'telegram.me'],
    }
    
    def scrape(self, url: str) -> Dict[str, Any]:
        """Зібрати контактну інформацію з сайту"""
        logger.info(f"Збір контактних даних з {url}")
        
        company_data = {
            'emails': [],
            'phones': [],
            'addresses': [],
            'facebook_url': None,
            'instagram_url': None,
            'linkedin_url': None,
            'twitter_url': None,
            'youtube_url': None,
            'telegram_url': None,
            'company_name': None,
            'legal_name': None,
            'tax_id': None,
            'registration_number': None,
            'contact_forms': [],
            'support_chat': False,
            'working_hours': None,
        }
        
        try:
            if not self.safe_get(url):
                logger.error(f"Не вдалося завантажити {url}")
                return company_data
            
            # Отримуємо HTML
            page_source = self.get_page_source()
            if not page_source:
                logger.error("Не отримано HTML-вміст сторінки")
                return company_data
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Збираємо email-адреси
            company_data['emails'] = self._extract_emails(soup, page_source)
            
            # Збираємо телефони
            company_data['phones'] = self._extract_phones(soup, page_source)
            
            # Збираємо адреси
            company_data['addresses'] = self._extract_addresses(soup)
            
            # Збираємо соціальні мережі
            social_media = self._extract_social_media(soup, url)
            company_data.update(social_media)
            
            # Збираємо бізнес-інформацію
            business_info = self._extract_business_info(soup)
            company_data.update(business_info)
            
            # Шукаємо контактні форми
            company_data['contact_forms'] = self._find_contact_forms(soup, url)
            
            # Перевіряємо наявність чату підтримки
            company_data['support_chat'] = self._detect_support_chat(page_source)
            
            # Спробуємо знайти години роботи
            company_data['working_hours'] = self._extract_working_hours(soup)
            
            # Перевіряємо сторінку контактів
            contact_page_data = self._scrape_contact_page(url)
            company_data = self._merge_contact_data(company_data, contact_page_data)
            
            logger.info(f"Контактні дані успішно зібрано з {url}")
            
        except Exception as e:
            logger.error(f"Помилка збору контактних даних: {e}", exc_info=True)
        
        finally:
            self.close_driver()
        
        return company_data
    
    def _extract_emails(self, soup: BeautifulSoup, page_source: str) -> List[str]:
        """Витягти email-адреси"""
        emails: Set[str] = set()
        
        # Шукаємо в HTML
        found_emails = re.findall(self.EMAIL_PATTERN, page_source)
        emails.update(found_emails)
        
        # Шукаємо в mailto: посиланнях
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        for link in mailto_links:
            email = link.get('href', '').replace('mailto:', '').split('?')[0]
            if email:
                emails.add(email)
        
        # Фільтруємо неправильні email
        valid_emails = []
        for email in emails:
            email = email.lower().strip()
            # Пропускаємо email зображень та інші неправильні
            if not any(ext in email for ext in ['.png', '.jpg', '.gif', '.svg', 'example.com', 'domain.com']):
                if '@' in email and '.' in email.split('@')[-1]:
                    valid_emails.append(email)
        
        return list(set(valid_emails))[:10]  # Обмежуємо до 10
    
    def _extract_phones(self, soup: BeautifulSoup, page_source: str) -> List[str]:
        """Витягти телефони"""
        phones: Set[str] = set()
        
        # Шукаємо в tel: посиланнях
        tel_links = soup.find_all('a', href=re.compile(r'^tel:', re.I))
        for link in tel_links:
            phone = link.get('href', '').replace('tel:', '').strip()
            normalized = self._normalize_phone(phone)
            if normalized:
                phones.add(normalized)
        
        # Використовуємо phonenumbers для пошуку валідних UA-номерів у тексті
        matcher = PhoneNumberMatcher(page_source, "UA")
        for match in matcher:
            if phonenumbers.is_possible_number(match.number):
                formatted = phonenumbers.format_number(
                    match.number,
                    PhoneNumberFormat.INTERNATIONAL
                )
                phones.add(formatted)
        
        return list(phones)[:10]
    
    def _normalize_phone(self, phone: str) -> Optional[str]:
        """Привести телефон до єдиного формату або None"""
        if not phone:
            return None
        
        clean_phone = re.sub(r'[^\d+]', '', phone)
        if not clean_phone:
            return None
        
        try:
            parsed = phonenumbers.parse(clean_phone, "UA")
            if phonenumbers.is_possible_number(parsed):
                return phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
        except NumberParseException:
            return None
        
        return None
    
    def _extract_addresses(self, soup: BeautifulSoup) -> List[str]:
        """Витягти фізичні адреси"""
        addresses = []
        
        # Шукаємо в microdata
        address_tags = soup.find_all(attrs={'itemtype': re.compile(r'PostalAddress', re.I)})
        for addr in address_tags:
            address_text = addr.get_text(strip=True)
            if address_text and len(address_text) > 10:
                addresses.append(address_text)
        
        # Шукаємо за ключовими словами
        keywords = ['адреса', 'address', 'адрес', 'location', 'місцезнаходження']
        for keyword in keywords:
            # Шукаємо елементи з цими ключовими словами
            elements = soup.find_all(string=re.compile(keyword, re.I))
            for elem in elements[:5]:  # Обмежуємо пошук
                parent = elem.parent
                if parent:
                    text = parent.get_text(strip=True)
                    if 20 < len(text) < 200:  # Розумна довжина адреси
                        addresses.append(text)
        
        return list(set(addresses))[:5]
    
    def _extract_social_media(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Витягти посилання на соціальні мережі"""
        social = {
            'facebook_url': None,
            'instagram_url': None,
            'linkedin_url': None,
            'twitter_url': None,
            'youtube_url': None,
            'telegram_url': None,
        }
        
        # Знаходимо всі посилання
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '').lower()
            
            # Перевіряємо кожну соцмережу
            for platform, domains in self.SOCIAL_MEDIA.items():
                if social[f'{platform}_url']:  # Вже знайшли
                    continue
                
                for domain in domains:
                    if domain in href:
                        # Робимо абсолютний URL
                        absolute_url = urljoin(base_url, link.get('href'))
                        social[f'{platform}_url'] = absolute_url
                        break
        
        return social
    
    def _extract_business_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Витягти бізнес-інформацію"""
        info = {
            'company_name': None,
            'legal_name': None,
            'tax_id': None,
            'registration_number': None,
        }
        
        # Назва компанії з Schema.org
        org_name = soup.find(attrs={'itemprop': 'name'})
        if org_name:
            info['company_name'] = org_name.get_text(strip=True)
        
        # Пошук по ключових словах
        text = soup.get_text()
        
        # ЄДРПОУ / ІПН (Україна)
        edrpou_match = re.search(r'ЄДРПОУ[:\s]+(\d{8,10})', text, re.I)
        if edrpou_match:
            info['tax_id'] = edrpou_match.group(1)
        
        ipn_match = re.search(r'ІПН[:\s]+(\d{10,12})', text, re.I)
        if ipn_match:
            info['tax_id'] = ipn_match.group(1)
        
        return info
    
    def _find_contact_forms(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Знайти контактні форми"""
        forms = []
        
        # Знаходимо всі форми
        all_forms = soup.find_all('form')
        
        for form in all_forms:
            # Перевіряємо чи це контактна форма
            form_text = form.get_text().lower()
            if any(keyword in form_text for keyword in ['contact', 'контакт', 'message', 'повідомлення', 'email']):
                action = form.get('action', '')
                if action:
                    form_url = urljoin(base_url, action)
                    forms.append(form_url)
        
        return list(set(forms))
    
    def _detect_support_chat(self, page_source: str) -> bool:
        """Виявити наявність чату підтримки"""
        chat_indicators = [
            'intercom', 'tawk.to', 'zendesk', 'livechat', 
            'drift', 'crisp', 'olark', 'chat-widget',
            'онлайн-чат', 'live-chat'
        ]
        
        page_lower = page_source.lower()
        return any(indicator in page_lower for indicator in chat_indicators)
    
    def _extract_working_hours(self, soup: BeautifulSoup) -> str:
        """Витягти години роботи"""
        # Шукаємо за Schema.org
        hours_tag = soup.find(attrs={'itemprop': 'openingHours'})
        if hours_tag:
            return hours_tag.get('content') or hours_tag.get_text(strip=True)
        
        # Шукаємо за ключовими словами
        keywords = ['години роботи', 'working hours', 'режим роботи', 'графік роботи']
        for keyword in keywords:
            elements = soup.find_all(string=re.compile(keyword, re.I))
            for elem in elements:
                parent = elem.parent
                if parent:
                    text = parent.get_text(strip=True)
                    if 10 < len(text) < 200:
                        return text
        
        return None
    
    def _scrape_contact_page(self, base_url: str) -> Dict[str, Any]:
        """Спробувати знайти та обробити сторінку контактів"""
        contact_pages = [
            '/contacts', '/contact', '/contact-us', '/contactus',
            '/контакти', '/контакты', '/about', '/про-нас'
        ]
        
        for page in contact_pages:
            contact_url = urljoin(base_url, page)
            try:
                if self.safe_get(contact_url):
                    page_source = self.get_page_source()
                    if not page_source:
                        continue
                    soup = BeautifulSoup(page_source, 'lxml')
                    
                    # Збираємо додаткові дані
                    extra_data = {
                        'emails': self._extract_emails(soup, page_source),
                        'phones': self._extract_phones(soup, page_source),
                        'addresses': self._extract_addresses(soup),
                    }
                    
                    if any(extra_data.values()):
                        return extra_data
            except Exception as e:
                logger.debug(f"Помилка обробки сторінки контактів {contact_url}: {e}")
                continue
        
        return {}
    
    def _merge_contact_data(self, data1: Dict, data2: Dict) -> Dict:
        """Об'єднати дані з різних джерел"""
        merged = data1.copy()
        
        for key in ['emails', 'phones', 'addresses']:
            if key in data2 and data2[key]:
                existing = set(merged.get(key, []))
                new_items = set(data2[key])
                merged[key] = list(existing.union(new_items))[:10]
        
        return merged
