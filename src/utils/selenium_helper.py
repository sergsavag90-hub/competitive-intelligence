"""
Допоміжний модуль для роботи з Selenium
"""

import asyncio
import time
import logging
import random
from typing import Optional, List
from contextlib import asynccontextmanager

import requests
from requests import Session, RequestException
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from .config import config

logger = logging.getLogger(__name__)


class SeleniumHelper:
    """Базовий клас для роботи з Selenium Grid"""
    
    def __init__(self, hub_url: Optional[str] = None, browser: Optional[str] = None):
        self.provider = config.selenium_provider
        self.hub_url = hub_url or config.selenium_hub_url
        self.browser = browser or config.selenium_browser
        self.browserless_api_key = config.selenium_browserless_api_key
        self.browserless_region = config.selenium_browserless_region
        self.fallback_percent = config.selenium_fallback_local_percent
        self.driver: Optional[WebDriver] = None
        self.mode = config.selenium_mode
        self.allow_requests_fallback = config.selenium_requests_fallback
        self._last_page_source: Optional[str] = None
        self._last_url: Optional[str] = None
        self._session: Optional[Session] = None
        self._semaphore = asyncio.Semaphore(config.selenium_max_concurrent)
        
    def get_driver(self) -> Optional[WebDriver]:
        """Створити та налаштувати WebDriver"""
        if self.mode == 'requests':
            logger.debug("Режим 'requests' не потребує WebDriver")
            return None
        
        try:
            options = self._get_browser_options()
            
            self.driver = webdriver.Remote(
                command_executor=self.hub_url,
                options=options
            )
            
            self.driver.implicitly_wait(config.implicit_wait)
            self.driver.set_page_load_timeout(config.page_load_timeout)
            
            logger.info(f"WebDriver створено успішно для {self.browser}")
            return self.driver
            
        except WebDriverException as e:
            logger.error(f"Помилка створення WebDriver: {e}")
            raise

    async def _health_check(self) -> bool:
        """Перевірка доступності Selenium Grid."""
        if self.provider == "browserless":
            # Browserless manages scaling; assume available if API key exists
            return bool(self.browserless_api_key)
        try:
            resp = requests.get(f"{self.hub_url}/status", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def _create_driver_sync(self) -> WebDriver:
        options = self._get_browser_options()
        endpoint = self._choose_endpoint()
        driver = webdriver.Remote(command_executor=endpoint, options=options)
        driver.implicitly_wait(config.implicit_wait)
        driver.set_page_load_timeout(min(config.page_load_timeout, 30))
        return driver

    def _choose_endpoint(self) -> str:
        """Select primary (browserless) or fallback selenium endpoint based on config."""
        if self.provider == "browserless" and self.browserless_api_key:
            # 0-100 scale percent routed to local fallback
            if random.uniform(0, 100) > self.fallback_percent:
                return self._browserless_endpoint()
        return self.hub_url

    def _browserless_endpoint(self) -> str:
        base = self.hub_url
        # If user did not override hub_url, derive from region
        if "browserless" not in base:
            base = f"https://{self.browserless_region}.browserless.io"
        if not base.endswith("/webdriver"):
            base = f"{base.rstrip('/')}/webdriver"
        token = self.browserless_api_key
        return f"{base}?token={token}"

    async def _safe_quit(self, driver: WebDriver):
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, driver.quit)
        except Exception as exc:
            logger.debug("Error quitting driver: %s", exc)

    @asynccontextmanager
    async def driver_context(self):
        """Async context manager з обмеженням на 10 драйверів та авто-cleanup."""
        healthy = await self._health_check()
        if not healthy:
            raise RuntimeError("Selenium Grid is not healthy")

        loop = asyncio.get_running_loop()
        driver: Optional[WebDriver] = None
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=30)
            driver = await asyncio.wait_for(loop.run_in_executor(None, self._create_driver_sync), timeout=30)
            yield driver
        finally:
            if driver:
                await self._safe_quit(driver)
            if self._semaphore.locked():
                self._semaphore.release()
    
    def _get_browser_options(self):
        """Отримати опції браузера"""
        if self.browser.lower() == 'chrome':
            options = webdriver.ChromeOptions()
            if config.selenium_headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            return options
            
        elif self.browser.lower() == 'firefox':
            options = webdriver.FirefoxOptions()
            if config.selenium_headless:
                options.add_argument('--headless')
            options.add_argument('--width=1920')
            options.add_argument('--height=1080')
            return options
            
        else:
            raise ValueError(f"Непідтримуваний браузер: {self.browser}")
    
    def safe_get(self, url: str, retries: int = 3) -> bool:
        """Безпечне завантаження URL з повторними спробами"""
        if self.mode == 'requests':
            return self._fetch_via_requests(url)
        
        for attempt in range(retries):
            try:
                if not self.driver:
                    self.driver = self.get_driver()
                
                logger.info(f"Завантаження URL: {url} (спроба {attempt + 1}/{retries})")
                self.driver.get(url)
                
                # Чекаємо завантаження DOM
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                self._last_page_source = self.driver.page_source
                self._last_url = url
                return True
                
            except Exception as e:
                logger.warning(f"Помилка завантаження {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(config.retry_delay)
                else:
                    logger.error(f"Не вдалося завантажити {url} після {retries} спроб")
                    if self.allow_requests_fallback:
                        logger.info("Переходимо у режим HTTP-запитів")
                        return self._fetch_via_requests(url)
                    return False
        
        return False

    def _fetch_via_requests(self, url: str) -> bool:
        """Отримати сторінку напряму через HTTP"""
        if not self._session:
            self._session = requests.Session()
        
        headers = {
            'User-Agent': config.user_agent,
        }
        
        try:
            logger.info(f"HTTP-запит: {url}")
            response = self._session.get(
                url,
                headers=headers,
                timeout=config.request_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            self._last_page_source = response.text
            self._last_url = response.url
            return True
        except RequestException as exc:
            logger.error(f"HTTP-запит не вдався для {url}: {exc}")
            return False
    
    def find_elements_safe(self, by: By, value: str, timeout: int = 5) -> List:
        """Безпечний пошук елементів з очікуванням"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            logger.debug(f"Елементи не знайдено: {by}={value}")
            return []
    
    def find_element_safe(self, by: By, value: str, timeout: int = 5):
        """Безпечний пошук одного елемента"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.debug(f"Елемент не знайдено: {by}={value}")
            return None
    
    def get_text_safe(self, by: By, value: str, default: str = "") -> str:
        """Безпечне отримання тексту елемента"""
        element = self.find_element_safe(by, value)
        return element.text if element else default
    
    def scroll_to_bottom(self, pause_time: float = 1.0):
        """Прокрутка сторінки вниз"""
        if not self.driver:
            return
            
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def take_screenshot(self, filename: str) -> bool:
        """Зробити скріншот сторінки"""
        if not self.driver:
            return False
            
        try:
            self.driver.save_screenshot(filename)
            logger.info(f"Скріншот збережено: {filename}")
            return True
        except Exception as e:
            logger.error(f"Помилка збереження скріншоту: {e}")
            return False
    
    def close_driver(self):
        """Закрити WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver закрито")
            except Exception as e:
                logger.warning(f"Помилка закриття WebDriver: {e}")
            finally:
                self.driver = None
        
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            finally:
                self._session = None
    
    def get_page_source(self) -> str:
        """Повернути останнє завантажене HTML-тіло"""
        if self.driver:
            return self.driver.page_source
        return self._last_page_source or ""
    
    def get_last_url(self) -> Optional[str]:
        """Повернути останній успішний URL (після редіректів)"""
        if self.driver:
            return getattr(self.driver, 'current_url', None)
        return self._last_url

    def __enter__(self):
        """Context manager вхід"""
        if self.mode != 'requests':
            self.get_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager вихід"""
        self.close_driver()
