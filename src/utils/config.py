"""
Конфігураційний модуль для завантаження та управління налаштуваннями
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List


class Config:
    """Клас для управління конфігурацією проєкту"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()
        
    def load_config(self) -> None:
        """Завантаження конфігурації з YAML файлу"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Конфігураційний файл не знайдено: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Отримати значення з конфігурації за ключем (підтримує вкладені ключі через крапку)"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
                
        return value if value is not None else default
    
    # Selenium Grid
    @property
    def selenium_hub_url(self) -> str:
        return self.get('selenium_grid.hub_url', 'http://localhost:4444/wd/hub')
    
    @property
    def selenium_mode(self) -> str:
        """Поточний режим Selenium: remote/local/requests"""
        return self.get('selenium_grid.mode', 'remote').lower()
    
    @property
    def selenium_requests_fallback(self) -> bool:
        """Чи дозволено падати назад до HTTP-запитів"""
        return self.get('selenium_grid.requests_fallback', True)
    
    @property
    def selenium_browser(self) -> str:
        return self.get('selenium_grid.browser', 'chrome')
    
    @property
    def selenium_headless(self) -> bool:
        return self.get('selenium_grid.headless', True)
    
    @property
    def implicit_wait(self) -> int:
        return self.get('selenium_grid.implicit_wait', 10)
    
    @property
    def page_load_timeout(self) -> int:
        return self.get('selenium_grid.page_load_timeout', 30)
    
    # Targets
    @property
    def targets(self) -> List[Dict[str, Any]]:
        return self.get('targets', [])
    
    def get_enabled_targets(self) -> List[Dict[str, Any]]:
        """Отримати список активних цілей"""
        return [t for t in self.targets if t.get('enabled', True)]
    
    # Modules
    def is_module_enabled(self, module_name: str) -> bool:
        """Перевірити, чи увімкнено модуль"""
        return self.get(f'modules.{module_name}.enabled', False)

    def get_seo_crawl_settings(self) -> Dict[str, Any]:
        """Отримати налаштування обходу для SEO"""
        return {
            'max_pages_to_crawl': self.get('modules.seo.max_pages_to_crawl', 50),
            'max_crawl_depth': self.get('modules.seo.max_crawl_depth', 3),
        }
    
    # Database
    @property
    def db_type(self) -> str:
        return self.get('database.type', 'sqlite')
    
    @property
    def db_path(self) -> str:
        return self.get('database.path', 'data/competitive_intelligence.db')
    
    # Ollama
    @property
    def ollama_enabled(self) -> bool:
        return self.get('ollama.enabled', False)
    
    @property
    def ollama_model(self) -> str:
        return self.get('ollama.model', 'llama3.2')
    
    @property
    def ollama_host(self) -> str:
        return self.get('ollama.host', 'http://localhost:11434')
    
    # Web interface
    @property
    def web_host(self) -> str:
        return self.get('web.host', '0.0.0.0')
    
    @property
    def web_port(self) -> int:
        return self.get('web.port', 5000)
    
    # Logging
    @property
    def log_level(self) -> str:
        return self.get('logging.level', 'INFO')
    
    @property
    def log_file(self) -> str:
        return self.get('logging.file', 'logs/intelligence.log')
    
    # Scraping settings
    @property
    def parallel_workers(self) -> int:
        return self.get('scraping.parallel_workers', 3)
    
    @property
    def retry_attempts(self) -> int:
        return self.get('scraping.retry_attempts', 3)
    
    @property
    def retry_delay(self) -> int:
        return self.get('scraping.retry_delay', 5)
    
    @property
    def request_timeout(self) -> int:
        return self.get(
            'scraping.request_timeout',
            self.get('selenium_grid.request_timeout', 30)
        )
    
    @property
    def user_agent(self) -> str:
        return self.get(
            'scraping.user_agent', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )


# Глобальний екземпляр конфігурації
config = Config()
