"""
Base Scraper Module

Implements multi-threaded web scraping using Selenium Grid and concurrent.futures
for handling parallel browser sessions with robust error handling and resource management.
"""

import logging
import time
import traceback
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from threading import Lock, Event
from queue import Queue, Empty
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)

from src.utils.config import config
from src.utils.retry_handler import build_retrying
from src.utils.circuit_breaker import SeleniumCircuitBreaker
from src.utils.dlq_manager import DeadLetterQueue

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ScraperConfig:
    """Configuration container for scraper settings."""

    def __init__(
        self,
        grid_url: str = None,
        max_workers: int = None,
        timeout: int = None,
        implicit_wait: int = None,
        page_load_timeout: int = None,
        max_retries: int = None,
        retry_delay: float = None,
        headless: bool = None,
        browser: str = None,
    ):
        """
        Initialize scraper configuration.

        Args:
            grid_url: Selenium Grid hub URL
            max_workers: Maximum number of parallel browser sessions
            timeout: Default timeout for element waits (seconds)
            implicit_wait: Implicit wait time for elements (seconds)
            page_load_timeout: Page load timeout (seconds)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries (seconds)
            headless: Run browser in headless mode
            browser: Browser type ('chrome', 'firefox', 'edge')
        """
        self.grid_url = grid_url or config.selenium_hub_url
        self.max_workers = max_workers or config.parallel_workers
        self.timeout = timeout or config.page_load_timeout
        self.implicit_wait = implicit_wait or config.implicit_wait
        self.page_load_timeout = page_load_timeout or config.page_load_timeout
        self.max_retries = max_retries or config.retry_attempts
        self.retry_delay = retry_delay or config.retry_delay
        self.headless = headless if headless is not None else config.selenium_headless
        self.browser = (browser or config.selenium_browser).lower()


class BrowserSessionPool:
    """Thread-safe pool for managing browser sessions."""

    def __init__(self, config: ScraperConfig):
        """
        Initialize browser session pool.

        Args:
            config: Scraper configuration
        """
        self.config = config
        self.available_sessions: Queue = Queue(maxsize=config.max_workers)
        self.active_sessions: Set[WebDriver] = set()
        self.lock = Lock()
        self.closed = False

    def acquire_session(self, timeout: int = 10) -> Optional[WebDriver]:
        """
        Acquire a browser session from the pool.

        Args:
            timeout: Timeout for acquiring session (seconds)

        Returns:
            WebDriver instance or None if timeout
        """
        try:
            session = self.available_sessions.get(timeout=timeout)
            return session
        except Empty:
            # Create new session if pool is empty
            return self._create_session()

    def release_session(self, session: WebDriver) -> None:
        """
        Release a browser session back to the pool.

        Args:
            session: WebDriver instance to release
        """
        if not self.closed and session:
            try:
                self.available_sessions.put(session, block=False)
            except Exception as e:
                logger.warning(f"Failed to return session to pool: {e}")
                self._close_session(session)

    def _create_session(self) -> Optional[WebDriver]:
        """
        Create a new browser session.

        Returns:
            WebDriver instance or None if creation fails
        """
        with self.lock:
            if len(self.active_sessions) >= self.config.max_workers:
                return None

            try:
                options = self._get_browser_options()
                driver = webdriver.Remote(
                    command_executor=self.config.grid_url,
                    options=options,
                )

                driver.set_implicit_wait(self.config.implicit_wait)
                driver.set_page_load_timeout(self.config.page_load_timeout)

                self.active_sessions.add(driver)
                logger.debug(f"Created new browser session. Total active: {len(self.active_sessions)}")
                return driver

            except WebDriverException as e:
                logger.error(f"Failed to create browser session: {e}")
                return None

    def _get_browser_options(self):
        """Get browser options based on configuration."""
        if self.config.browser == "chrome":
            from selenium.webdriver.chrome.options import Options
            options = Options()
        elif self.config.browser == "firefox":
            from selenium.webdriver.firefox.options import Options
            options = Options()
        elif self.config.browser == "edge":
            from selenium.webdriver.edge.options import Options
            options = Options()
        else:
            from selenium.webdriver.chrome.options import Options
            options = Options()

        if self.config.headless:
            options.add_argument("--headless")

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        return options

    def _close_session(self, session: WebDriver) -> None:
        """Close a browser session."""
        try:
            session.quit()
        except Exception as e:
            logger.warning(f"Error closing session: {e}")
        finally:
            with self.lock:
                self.active_sessions.discard(session)

    def close_all(self) -> None:
        """Close all browser sessions in the pool."""
        with self.lock:
            self.closed = True
            for session in list(self.active_sessions):
                self._close_session(session)

            # Drain remaining sessions from queue
            while not self.available_sessions.empty():
                try:
                    session = self.available_sessions.get_nowait()
                    self._close_session(session)
                except Empty:
                    break

            logger.info("All browser sessions closed")


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers with multi-threaded capabilities.

    Provides thread-safe browser session management, parallel task execution,
    retry logic, and comprehensive error handling.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize the base scraper.

        Args:
            config: ScraperConfig instance (uses defaults if None)
        """
        self.config = config or ScraperConfig()
        self.session_pool = BrowserSessionPool(self.config)
        self.executor: Optional[ThreadPoolExecutor] = None
        self._shutdown = Event()
        self.circuit_breaker = SeleniumCircuitBreaker(threshold=5, reset_timeout=60)
        self.dlq = DeadLetterQueue()
        self.retrying = build_retrying(max_attempts=3)
        self.metrics = ScraperMetrics()
        logger.info(f"Initialized {self.__class__.__name__} with config: max_workers={self.config.max_workers}")

    @abstractmethod
    def process_url(self, driver: WebDriver, url: str) -> Dict[str, Any]:
        """
        Process a single URL using the provided WebDriver.

        Args:
            driver: Selenium WebDriver instance
            url: URL to process

        Returns:
            Dictionary containing processed data
        """
        pass

    def scrape_urls(
        self,
        urls: List[str],
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in parallel.

        Args:
            urls: List of URLs to scrape
            callback: Optional callback function for each completed task

        Returns:
            List of dictionaries containing scraped data
        """
        self.metrics.start()
        results = []
        failed_urls = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            self.executor = executor
            futures = {
                executor.submit(self._scrape_with_retry, url): url
                for url in urls
            }

            completed = 0
            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        if callback:
                            callback(result)
                    else:
                        failed_urls.append(url)
                except Exception as e:
                    logger.error(f"Task failed for {url}: {e}")
                    failed_urls.append(url)

                completed += 1
                logger.debug(f"Progress: {completed}/{len(urls)} completed")

        self.executor = None

        self.metrics.end()
        if failed_urls:
            logger.warning(f"Failed to scrape {len(failed_urls)} URLs: {failed_urls}")

        return results

    def _scrape_with_retry(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a URL with retry logic.

        Args:
            url: URL to scrape

        Returns:
            Dictionary containing scraped data or None if failed
        """
        if not self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker OPEN; skipping %s", url)
            return None

        browsers_to_try = [self.config.browser]
        if self.config.browser == "chrome":
            browsers_to_try.append("firefox")  # graceful fallback

        for browser in browsers_to_try:
            self.config.browser = browser
            try:
                for attempt, retry_state in enumerate(self.retrying, start=1):
                    if self._shutdown.is_set():
                        logger.info("Shutdown signal received, stopping retry attempts")
                        return None
                    try:
                        driver = self.session_pool.acquire_session()
                        if not driver:
                            raise WebDriverException("Could not acquire browser session")

                        with retry_state:
                            logger.debug(f"Scraping {url} (attempt {attempt}) [{browser}]")
                            result = self.process_url(driver, url)
                            result["url"] = url
                            result["timestamp"] = datetime.utcnow().isoformat()
                            self.circuit_breaker.record_success()
                            self.metrics.record_success()
                            return result
                    except (TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
                        self.circuit_breaker.record_failure()
                        self.metrics.record_failure()
                        logger.warning(f"Retriable error for {url}: {type(e).__name__} [{browser}]")
                        raise
                    except Exception as e:
                        self.circuit_breaker.record_failure()
                        self.metrics.record_failure()
                        trace = traceback.format_exc()
                        self.dlq.add(
                            {
                                "url": url,
                                "browser": browser,
                                "error": str(e),
                                "traceback": trace,
                            }
                        )
                        logger.error(f"Error scraping {url}: {e}")
                        raise
                    finally:
                        try:
                            self.session_pool.release_session(driver)
                        except Exception:
                            pass
            except Exception:
                continue  # try next browser (fallback)

        # If all browsers failed, record to DLQ once more
        self.dlq.add({"url": url, "browser": "all", "error": "All retries failed"})
        return None

    def wait_for_element(
        self,
        driver: WebDriver,
        by: By,
        value: str,
        timeout: Optional[int] = None,
    ):
        """
        Wait for an element to be present.

        Args:
            driver: Selenium WebDriver instance
            by: Locator strategy (By.ID, By.XPATH, etc.)
            value: Locator value
            timeout: Timeout in seconds

        Returns:
            WebElement or None if timeout
        """
        timeout = timeout or self.config.timeout
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {by}={value}")
            return None

    def wait_for_elements(
        self,
        driver: WebDriver,
        by: By,
        value: str,
        timeout: Optional[int] = None,
    ) -> List:
        """
        Wait for multiple elements to be present.

        Args:
            driver: Selenium WebDriver instance
            by: Locator strategy (By.ID, By.XPATH, etc.)
            value: Locator value
            timeout: Timeout in seconds

        Returns:
            List of WebElements or empty list if timeout
        """
        timeout = timeout or self.config.timeout
        try:
            elements = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return elements
        except TimeoutException:
            logger.warning(f"Timeout waiting for elements: {by}={value}")
            return []

    def batch_scrape(
        self,
        urls: List[str],
        batch_size: int = 10,
        batch_delay: float = 1.0,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape URLs in batches with delay between batches.

        Args:
            urls: List of URLs to scrape
            batch_size: Number of URLs per batch
            batch_delay: Delay between batches (seconds)
            callback: Optional callback function for each completed task

        Returns:
            List of dictionaries containing scraped data
        """
        all_results = []

        for i in range(0, len(urls), batch_size):
            if self._shutdown.is_set():
                logger.info("Shutdown signal received, stopping batch processing")
                break

            batch = urls[i : i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}: {len(batch)} URLs")

            batch_results = self.scrape_urls(batch, callback)
            all_results.extend(batch_results)

            if i + batch_size < len(urls):
                time.sleep(batch_delay)

        return all_results

    def shutdown(self) -> None:
        """Gracefully shutdown the scraper."""
        logger.info("Initiating graceful shutdown")
        self._shutdown.set()

        if self.executor:
            self.executor.shutdown(wait=True)

        self.session_pool.close_all()
        logger.info("Scraper shutdown complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


class ScraperMetrics:
    """Tracks scraper performance metrics."""

    def __init__(self):
        """Initialize metrics tracker."""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.urls_processed = 0
        self.urls_failed = 0
        self.total_data_points = 0
        self.total_retries = 0
        self.lock = Lock()

    def start(self) -> None:
        """Mark scraping start."""
        with self.lock:
            self.start_time = datetime.utcnow()

    def end(self) -> None:
        """Mark scraping end."""
        with self.lock:
            self.end_time = datetime.utcnow()

    def record_success(self, data_points: int = 1, retries: int = 1) -> None:
        """Record successful scrape."""
        with self.lock:
            self.urls_processed += 1
            self.total_data_points += data_points
            self.total_retries += max(retries, 1)

    def record_failure(self, retries: int = 1) -> None:
        """Record failed scrape."""
        with self.lock:
            self.urls_failed += 1
            self.total_retries += max(retries, 1)

    def get_duration(self) -> Optional[timedelta]:
        """Get scraping duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        with self.lock:
            duration = self.get_duration()
            duration_seconds = duration.total_seconds() if duration else 0
            rate = (
                self.urls_processed / duration_seconds
                if duration_seconds > 0
                else 0
            )

            return {
                "urls_processed": self.urls_processed,
                "urls_failed": self.urls_failed,
                "total_urls": self.urls_processed + self.urls_failed,
                "total_data_points": self.total_data_points,
                "avg_retry_count": self.total_retries / max(self.urls_processed + self.urls_failed, 1),
                "duration_seconds": duration_seconds,
                "urls_per_second": rate,
                "success_rate": (
                    self.urls_processed / (self.urls_processed + self.urls_failed) * 100
                    if (self.urls_processed + self.urls_failed) > 0
                    else 0
                ),
            }
