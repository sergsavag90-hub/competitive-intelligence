"""
Company Data Extractor Module

This module provides functionality to extract valuable company information from
competitor websites including emails, phone numbers, social media links, and addresses.
"""

import re
from typing import List, Dict, Set, Optional
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, asdict
import json


@dataclass
class CompanyData:
    """Data class to store extracted company information."""
    url: str
    emails: List[str]
    phone_numbers: List[str]
    social_media: Dict[str, str]
    addresses: List[str]
    extraction_timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class CompanyExtractor:
    """
    Main class for extracting company data from website content.
    """
    
    # Regex patterns for data extraction
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    PHONE_PATTERNS = {
        'US': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        'INTL': r'\b\+?[1-9]\d{1,14}\b',
        'GENERIC': r'\b(?:\+\d{1,3}[-.\s]?)?\(?[0-9]{2,4}\)?[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{2,4}\b'
    }
    
    SOCIAL_MEDIA_PATTERNS = {
        'facebook': r'(?:https?://)?(?:www\.)?facebook\.com/[\w\-\.]+',
        'twitter': r'(?:https?://)?(?:www\.)?twitter\.com/[\w]+',
        'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/[\w\-]+',
        'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/[\w\.]+',
        'youtube': r'(?:https?://)?(?:www\.)?youtube\.com/(?:c|channel|user)/[\w\-]+',
        'github': r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+',
        'tiktok': r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w\.]+',
        'pinterest': r'(?:https?://)?(?:www\.)?pinterest\.com/[\w\-]+',
    }
    
    # Address patterns (simplified patterns for common address formats)
    ADDRESS_PATTERNS = {
        'street_address': r'\d+\s+[A-Za-z]+\s+(?:Street|Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Court|Ct\.?|Circle|Cir\.?)',
        'city_state_zip': r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?',
        'international_address': r'(?:[0-9]+\s+)?[A-Za-z\s]+,\s+[A-Za-z\s]+,\s+\d+',
    }
    
    def __init__(self):
        """Initialize the Company Extractor."""
        self.compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict:
        """Pre-compile all regex patterns for better performance."""
        return {
            'email': re.compile(self.EMAIL_PATTERN, re.IGNORECASE),
            'phone': {
                'us': re.compile(self.PHONE_PATTERNS['US'], re.IGNORECASE),
                'intl': re.compile(self.PHONE_PATTERNS['INTL'], re.IGNORECASE),
                'generic': re.compile(self.PHONE_PATTERNS['GENERIC'], re.IGNORECASE),
            },
            'social_media': {
                platform: re.compile(pattern, re.IGNORECASE)
                for platform, pattern in self.SOCIAL_MEDIA_PATTERNS.items()
            },
            'address': {
                addr_type: re.compile(pattern, re.IGNORECASE)
                for addr_type, pattern in self.ADDRESS_PATTERNS.items()
            }
        }
    
    def extract_emails(self, text: str) -> List[str]:
        """
        Extract email addresses from text.
        
        Args:
            text: Text to search for emails
            
        Returns:
            List of unique email addresses
        """
        emails = self.compiled_patterns['email'].findall(text)
        # Filter out common false positives
        filtered_emails = [
            email for email in emails
            if not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))
            and 'example' not in email.lower()
            and 'test' not in email.lower()
        ]
        return list(set(filtered_emails))  # Return unique emails
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """
        Extract phone numbers from text using multiple patterns.
        
        Args:
            text: Text to search for phone numbers
            
        Returns:
            List of unique phone numbers
        """
        phone_numbers = set()
        
        # Try US format first
        us_matches = self.compiled_patterns['phone']['us'].findall(text)
        for match in us_matches:
            if isinstance(match, tuple):
                phone = f"({match[0]}) {match[1]}-{match[2]}"
            else:
                phone = match
            phone_numbers.add(phone)
        
        # Try international format
        intl_matches = self.compiled_patterns['phone']['intl'].findall(text)
        phone_numbers.update(intl_matches)
        
        # Try generic format for remaining patterns
        generic_matches = self.compiled_patterns['phone']['generic'].findall(text)
        phone_numbers.update(generic_matches)
        
        return list(phone_numbers)
    
    def extract_social_media(self, text: str) -> Dict[str, List[str]]:
        """
        Extract social media links from text.
        
        Args:
            text: Text to search for social media links
            
        Returns:
            Dictionary with platform names and lists of found links
        """
        social_media = {}
        
        for platform, pattern in self.compiled_patterns['social_media'].items():
            matches = pattern.findall(text)
            if matches:
                # Remove duplicates and ensure URLs start with http
                links = set()
                for match in matches:
                    if not match.startswith('http'):
                        match = f"https://{match}"
                    links.add(match)
                social_media[platform] = list(links)
        
        return social_media
    
    def extract_addresses(self, text: str) -> List[str]:
        """
        Extract addresses from text using multiple patterns.
        
        Args:
            text: Text to search for addresses
            
        Returns:
            List of potential addresses
        """
        addresses = set()
        
        # Try each address pattern
        for addr_type, pattern in self.compiled_patterns['address'].items():
            matches = pattern.findall(text)
            addresses.update(matches)
        
        return list(addresses)
    
    def extract_all(self, text: str, url: str = "", timestamp: Optional[str] = None) -> CompanyData:
        """
        Extract all company data from text in one operation.
        
        Args:
            text: Text content to extract from
            url: Optional URL of the source website
            timestamp: Optional timestamp of extraction
            
        Returns:
            CompanyData object containing all extracted information
        """
        return CompanyData(
            url=url,
            emails=self.extract_emails(text),
            phone_numbers=self.extract_phone_numbers(text),
            social_media=self.extract_social_media(text),
            addresses=self.extract_addresses(text),
            extraction_timestamp=timestamp
        )


class WebsiteAnalyzer:
    """
    High-level analyzer for extracting company data from websites.
    """
    
    def __init__(self):
        """Initialize the Website Analyzer."""
        self.extractor = CompanyExtractor()
    
    def analyze_competitor(self, text: str, website_url: str, timestamp: Optional[str] = None) -> CompanyData:
        """
        Analyze a competitor's website content and extract company data.
        
        Args:
            text: Website content/HTML
            website_url: URL of the competitor website
            timestamp: Optional extraction timestamp
            
        Returns:
            CompanyData object with extracted information
        """
        # Remove HTML tags for better extraction
        clean_text = self._clean_html(text)
        
        # Extract all data
        company_data = self.extractor.extract_all(clean_text, url=website_url, timestamp=timestamp)
        
        return company_data
    
    def _clean_html(self, html_text: str) -> str:
        """
        Remove HTML tags and decode HTML entities.
        
        Args:
            html_text: Raw HTML text
            
        Returns:
            Cleaned text
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_text)
        
        # Replace common HTML entities
        replacements = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
        }
        
        for entity, char in replacements.items():
            text = text.replace(entity, char)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def compare_competitors(self, competitors_data: List[CompanyData]) -> Dict:
        """
        Compare extracted data from multiple competitors.
        
        Args:
            competitors_data: List of CompanyData objects
            
        Returns:
            Dictionary with comparison analysis
        """
        comparison = {
            'total_competitors': len(competitors_data),
            'all_emails': set(),
            'all_phone_numbers': set(),
            'all_social_media_platforms': set(),
            'competitors': []
        }
        
        for company in competitors_data:
            comparison['all_emails'].update(company.emails)
            comparison['all_phone_numbers'].update(company.phone_numbers)
            comparison['all_social_media_platforms'].update(company.social_media.keys())
            
            comparison['competitors'].append({
                'url': company.url,
                'email_count': len(company.emails),
                'phone_count': len(company.phone_numbers),
                'social_media_count': len(company.social_media),
                'address_count': len(company.addresses)
            })
        
        # Convert sets to lists for JSON serialization
        comparison['all_emails'] = list(comparison['all_emails'])
        comparison['all_phone_numbers'] = list(comparison['all_phone_numbers'])
        comparison['all_social_media_platforms'] = list(comparison['all_social_media_platforms'])
        
        return comparison


# Utility functions
def extract_domain_from_url(url: str) -> str:
    """
    Extract domain name from URL.
    
    Args:
        url: Website URL
        
    Returns:
        Domain name
    """
    parsed = urlparse(url)
    return parsed.netloc or parsed.path


def is_valid_email(email: str) -> bool:
    """
    Validate if string is a valid email format.
    
    Args:
        email: Email string to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    pattern = re.compile(CompanyExtractor.EMAIL_PATTERN)
    return pattern.match(email) is not None


def is_valid_phone(phone: str) -> bool:
    """
    Validate if string is a valid phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid phone format, False otherwise
    """
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.+]', '', phone)
    return 7 <= len(cleaned) <= 15


if __name__ == "__main__":
    # Example usage
    sample_html = """
    <html>
        <body>
            <p>Contact us at info@company.com or support@company.com</p>
            <p>Phone: (555) 123-4567 or +1-555-987-6543</p>
            <p>Address: 123 Main Street, New York, NY 10001</p>
            <p>Follow us on:</p>
            <a href="https://www.facebook.com/company">Facebook</a>
            <a href="https://www.linkedin.com/company/mycompany">LinkedIn</a>
            <a href="https://www.twitter.com/company">Twitter</a>
        </body>
    </html>
    """
    
    analyzer = WebsiteAnalyzer()
    result = analyzer.analyze_competitor(sample_html, "https://example.com")
    
    print("Extracted Company Data:")
    print(result.to_json())
