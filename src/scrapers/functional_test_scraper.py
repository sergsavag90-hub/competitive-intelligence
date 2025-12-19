"""
Functional Test Scraper Module

Implements a scraper to perform synthetic transactions like registration and form submission
on target websites using the BaseScraper infrastructure.
"""

import logging
from typing import Any, Dict, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from ..base_scraper import BaseScraper, ScraperConfig

logger = logging.getLogger(__name__)


class FunctionalTestScraper(BaseScraper):
    """
    Scraper for testing registration and form submission functionality.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        logger.info("FunctionalTestScraper initialized.")

    def process_url(self, driver: WebDriver, url: str) -> Dict[str, Any]:
        """
        Performs registration and form submission tests on the given URL.
        
        Args:
            driver: Selenium WebDriver instance.
            url: URL to test.

        Returns:
            Dictionary containing test results.
        """
        results = {
            "url": url,
            "registration_test": {"status": "skipped", "message": "No registration form found"},
            "contact_form_test": {"status": "skipped", "message": "No contact form found"},
        }

        try:
            # 1. Navigate to the URL
            logger.info(f"Navigating to {url}")
            driver.get(url)
            
            # 2. Attempt Registration Test
            results["registration_test"] = self._test_registration(driver)
            
            # 3. Attempt Contact Form Test (simple form submission)
            # Re-navigate or find a different page if needed, but for simplicity, we test on the main page first
            if results["registration_test"]["status"] != "success":
                driver.get(url) # Reload page if registration failed or was skipped
                results["contact_form_test"] = self._test_contact_form(driver)

        except TimeoutException:
            results["status"] = "failed"
            results["message"] = "Page load timed out."
            logger.error(f"Timeout while loading {url}")
        except WebDriverException as e:
            results["status"] = "failed"
            results["message"] = f"WebDriver error: {e}"
            logger.error(f"WebDriver error for {url}: {e}")
        except Exception as e:
            results["status"] = "failed"
            results["message"] = f"An unexpected error occurred: {e}"
            logger.error(f"Unexpected error for {url}: {e}")
            
        return results

    def _test_registration(self, driver: WebDriver) -> Dict[str, str]:
        """Simulate a user registration attempt."""
        test_result = {"status": "failed", "message": "Initial state"}
        
        try:
            # Try to find a common registration link/button
            try:
                # Look for a 'Register' or 'Sign Up' link/button
                reg_link = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign up')] | //button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign up')]"))
                )
                reg_link.click()
                logger.info("Clicked on registration link/button.")
            except TimeoutException:
                # Try to find the form directly on the page
                pass

            # Wait for the registration form to appear (look for email and password fields)
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @name='email' or @id='email']"))
            )
            password_field = driver.find_element(By.XPATH, "//input[@type='password' or @name='password' or @id='password']")
            submit_button = driver.find_element(By.XPATH, "//button[@type='submit' or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign up')]")

            # Fill the form
            timestamp = str(int(self.config.timeout * time.time())) # Use a unique timestamp
            test_email = f"testuser_{timestamp}@example.com"
            test_password = "TestPassword123!"
            
            email_field.send_keys(test_email)
            password_field.send_keys(test_password)
            
            # If there's a name field, fill it
            try:
                name_field = driver.find_element(By.XPATH, "//input[@type='text' and (@name='name' or @id='name' or @name='username' or @id='username')]")
                name_field.send_keys(f"Test User {timestamp}")
            except NoSuchElementException:
                pass # Name field is optional

            logger.info(f"Attempting registration with email: {test_email}")
            submit_button.click()

            # Wait for success or error
            WebDriverWait(driver, 10).until(
                lambda d: "success" in d.current_url.lower() or 
                          "dashboard" in d.current_url.lower() or 
                          "error" in d.page_source.lower() or
                          "already exists" in d.page_source.lower()
            )
            
            # Simple check: if URL changed or no obvious error, assume success (or partial success)
            if "error" not in driver.page_source.lower() and "already exists" not in driver.page_source.lower():
                test_result["status"] = "success"
                test_result["message"] = f"Registration form submitted successfully. Current URL: {driver.current_url}"
            else:
                test_result["status"] = "failed"
                test_result["message"] = f"Registration failed. Error message found or user already exists. Current URL: {driver.current_url}"

        except TimeoutException:
            test_result["status"] = "skipped"
            test_result["message"] = "Registration form elements not found within timeout."
        except NoSuchElementException as e:
            test_result["status"] = "skipped"
            test_result["message"] = f"Registration form element not found: {e}"
        except Exception as e:
            test_result["status"] = "error"
            test_result["message"] = f"An error occurred during registration test: {e}"
            
        return test_result

    def _test_contact_form(self, driver: WebDriver) -> Dict[str, str]:
        """Simulate a simple contact form submission."""
        test_result = {"status": "failed", "message": "Initial state"}
        
        try:
            # Try to find a contact link/button
            try:
                contact_link = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'зв')]"))
                )
                contact_link.click()
                logger.info("Clicked on contact link/button.")
            except TimeoutException:
                # Try to find the form directly on the page
                pass

            # Wait for the contact form to appear (look for a textarea or message field)
            message_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@name='message' or @id='message' or @name='body' or @id='body']"))
            )
            
            # Find email and submit button
            email_field = driver.find_element(By.XPATH, "//input[@type='email' or @name='email' or @id='email']")
            submit_button = driver.find_element(By.XPATH, "//button[@type='submit' or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'відправити')]")

            # Fill the form
            timestamp = str(int(self.config.timeout * time.time()))
            test_email = f"contact_{timestamp}@example.com"
            test_message = "This is a synthetic test message from Competitive Intelligence Dashboard."
            
            email_field.send_keys(test_email)
            message_field.send_keys(test_message)

            logger.info(f"Attempting contact form submission with email: {test_email}")
            submit_button.click()

            # Wait for success message or redirect
            WebDriverWait(driver, 10).until(
                lambda d: "success" in d.page_source.lower() or 
                          "thank you" in d.page_source.lower() or 
                          "відправлено" in d.page_source.lower() or
                          "error" in d.page_source.lower()
            )
            
            # Simple check: if a success message is found, assume success
            if "success" in driver.page_source.lower() or "thank you" in driver.page_source.lower() or "відправлено" in driver.page_source.lower():
                test_result["status"] = "success"
                test_result["message"] = "Contact form submitted successfully and success message found."
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Contact form submitted, but no clear success message found or an error occurred."

        except TimeoutException:
            test_result["status"] = "skipped"
            test_result["message"] = "Contact form elements not found within timeout."
        except NoSuchElementException as e:
            test_result["status"] = "skipped"
            test_result["message"] = f"Contact form element not found: {e}"
        except Exception as e:
            test_result["status"] = "error"
            test_result["message"] = f"An error occurred during contact form test: {e}"
            
        return test_result

# Example usage (for testing purposes, not run in production)
if __name__ == "__main__":
    # This part is for local testing and should be removed or commented out in the final commit
    pass
