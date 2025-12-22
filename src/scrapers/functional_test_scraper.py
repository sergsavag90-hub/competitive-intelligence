"""
Functional Test Scraper Module

Implements a scraper to perform synthetic transactions like registration and form submission
on target websites using the BaseScraper infrastructure.
"""

import logging
import time
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
            # Try to find a common registration link/button - IMPROVED SELECTORS
            try:
                # Look for a 'Register' or 'Sign Up' link/button with better patterns
                reg_selectors = [
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register')]",
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign up')]",
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'signup')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign up')]",
                    "//a[contains(translate(text(), 'АБВГДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ', 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя'), 'реєстрація')]",
                    "//a[contains(translate(text(), 'АБВГДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ', 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя'), 'зареєструватися')]",
                    "//a[@href[contains(., 'register')] or @href[contains(., 'signup')]]",
                    "//button[@type='button' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register')]"
                ]
                
                reg_link = None
                for selector in reg_selectors:
                    try:
                        reg_link = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if reg_link:
                            break
                    except TimeoutException:
                        continue
                
                if reg_link:
                    reg_link.click()
                    logger.info("Clicked on registration link/button.")
                    time.sleep(2)  # Wait for page/modal to load
                    
            except Exception as e:
                logger.debug(f"Could not find registration link: {e}")
                # Try to find the form directly on the page

            # Wait for the registration form to appear (look for email and password fields) - IMPROVED SELECTORS
            email_selectors = [
                "//input[@type='email']",
                "//input[@name='email' or @id='email' or @id='Email']",
                "//input[contains(@placeholder, 'mail') or contains(@placeholder, 'Mail')]",
                "//input[contains(@name, 'email') or contains(@id, 'email')]"
            ]
            
            password_selectors = [
                "//input[@type='password']",
                "//input[@name='password' or @id='password' or @id='Password']",
                "//input[contains(@placeholder, 'password') or contains(@placeholder, 'Password')]"
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if email_field:
                        break
                except TimeoutException:
                    continue
            
            if not email_field:
                test_result["status"] = "skipped"
                test_result["message"] = "Registration email field not found."
                return test_result
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = driver.find_element(By.XPATH, selector)
                    if password_field:
                        break
                except NoSuchElementException:
                    continue
            
            if not password_field:
                test_result["status"] = "skipped"
                test_result["message"] = "Registration password field not found."
                return test_result

            # Find submit button - IMPROVED SELECTORS
            submit_selectors = [
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign up')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                "//input[@type='submit' and (contains(@value, 'register') or contains(@value, 'Register'))]"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = driver.find_element(By.XPATH, selector)
                    if submit_button:
                        break
                except NoSuchElementException:
                    continue
            
            if not submit_button:
                test_result["status"] = "skipped"
                test_result["message"] = "Registration submit button not found."
                return test_result

            # Fill the form
            timestamp = str(int(time.time()))
            test_email = f"testuser_{timestamp}@example.com"
            test_password = "TestPassword123!"
            
            email_field.clear()
            email_field.send_keys(test_email)
            password_field.clear()
            password_field.send_keys(test_password)
            
            # If there's a name field, fill it - IMPROVED SELECTORS
            name_selectors = [
                "//input[@type='text' and (@name='name' or @id='name')]",
                "//input[@name='username' or @id='username']",
                "//input[@name='first_name' or @id='first_name']",
                "//input[@name='firstname' or @id='firstname']",
                "//input[contains(@placeholder, 'name') or contains(@placeholder, 'Name')]"
            ]
            
            for selector in name_selectors:
                try:
                    name_field = driver.find_element(By.XPATH, selector)
                    if name_field:
                        name_field.clear()
                        name_field.send_keys(f"Test User {timestamp}")
                        break
                except NoSuchElementException:
                    continue

            logger.info(f"Attempting registration with email: {test_email}")
            submit_button.click()

            # Wait for success or error - IMPROVED DETECTION
            time.sleep(3)  # Give page time to process
            
            # Check for various success/error indicators
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()
            
            success_indicators = ['success', 'welcome', 'dashboard', 'confirm', 'verify', 'thank']
            error_indicators = ['error', 'already exists', 'invalid', 'failed', 'incorrect']
            
            has_success = any(indicator in page_source or indicator in current_url for indicator in success_indicators)
            has_error = any(indicator in page_source for indicator in error_indicators)
            
            if has_success and not has_error:
                test_result["status"] = "success"
                test_result["message"] = f"Registration form submitted successfully. Current URL: {driver.current_url}"
            elif has_error:
                test_result["status"] = "failed"
                test_result["message"] = f"Registration failed with error message. Current URL: {driver.current_url}"
            else:
                # Check if URL changed (might indicate success)
                if driver.current_url != current_url:
                    test_result["status"] = "partial"
                    test_result["message"] = f"Form submitted, URL changed but no clear success/error message. Current URL: {driver.current_url}"
                else:
                    test_result["status"] = "unknown"
                    test_result["message"] = "Form submitted but result unclear."

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
            # Try to find a contact link/button - IMPROVED SELECTORS
            try:
                contact_selectors = [
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact')]",
                    "//a[contains(translate(text(), 'АБВГДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ', 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя'), 'контакт')]",
                    "//a[contains(translate(text(), 'АБВГДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ', 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя'), "зв'язок")]",
                    "//a[@href[contains(., 'contact')]]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact')]"
                ]
                
                contact_link = None
                for selector in contact_selectors:
                    try:
                        contact_link = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if contact_link:
                            break
                    except TimeoutException:
                        continue
                
                if contact_link:
                    contact_link.click()
                    logger.info("Clicked on contact link/button.")
                    time.sleep(2)  # Wait for page/modal to load
                    
            except Exception as e:
                logger.debug(f"Could not find contact link: {e}")
                # Try to find the form directly on the page

            # Wait for the contact form to appear - IMPROVED SELECTORS
            message_selectors = [
                "//textarea[@name='message' or @id='message']",
                "//textarea[@name='body' or @id='body']",
                "//textarea[@name='comment' or @id='comment']",
                "//textarea[@name='text' or @id='text']",
                "//textarea[contains(@placeholder, 'message') or contains(@placeholder, 'Message')]",
                "//textarea[contains(@placeholder, 'повідомлення') or contains(@placeholder, 'Повідомлення')]"
            ]
            
            message_field = None
            for selector in message_selectors:
                try:
                    message_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if message_field:
                        break
                except TimeoutException:
                    continue
            
            if not message_field:
                test_result["status"] = "skipped"
                test_result["message"] = "Contact form message field not found."
                return test_result
            
            # Find email field - IMPROVED SELECTORS
            email_selectors = [
                "//input[@type='email']",
                "//input[@name='email' or @id='email' or @id='Email']",
                "//input[contains(@placeholder, 'mail') or contains(@placeholder, 'Mail')]",
                "//input[contains(@name, 'email') or contains(@id, 'email')]"
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = driver.find_element(By.XPATH, selector)
                    if email_field:
                        break
                except NoSuchElementException:
                    continue
            
            if not email_field:
                test_result["status"] = "skipped"
                test_result["message"] = "Contact form email field not found."
                return test_result
            
            # Find submit button - IMPROVED SELECTORS
            submit_selectors = [
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                "//button[contains(translate(text(), 'АБВГДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ', 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя'), 'відправити')]",
                "//button[contains(translate(text(), 'АБВГДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ', 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя'), 'надіслати')]",
                "//input[@type='submit' and (contains(@value, 'send') or contains(@value, 'Send'))]"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = driver.find_element(By.XPATH, selector)
                    if submit_button:
                        break
                except NoSuchElementException:
                    continue
            
            if not submit_button:
                test_result["status"] = "skipped"
                test_result["message"] = "Contact form submit button not found."
                return test_result

            # Fill the form
            timestamp = str(int(time.time()))
            test_email = f"contact_{timestamp}@example.com"
            test_message = "This is a synthetic test message from Competitive Intelligence Dashboard."
            
            # Find and fill name field if exists
            name_selectors = [
                "//input[@name='name' or @id='name']",
                "//input[@name='fullname' or @id='fullname']",
                "//input[@name='full_name' or @id='full_name']",
                "//input[contains(@placeholder, 'name') or contains(@placeholder, 'Name')]"
            ]
            
            for selector in name_selectors:
                try:
                    name_field = driver.find_element(By.XPATH, selector)
                    if name_field:
                        name_field.clear()
                        name_field.send_keys(f"Test User {timestamp}")
                        break
                except NoSuchElementException:
                    continue
            
            email_field.clear()
            email_field.send_keys(test_email)
            message_field.clear()
            message_field.send_keys(test_message)

            logger.info(f"Attempting contact form submission with email: {test_email}")
            submit_button.click()

            # Wait for success message or redirect - IMPROVED DETECTION
            time.sleep(3)  # Give page time to process
            
            page_source = driver.page_source.lower()
            
            success_indicators = [
                'success', 'thank you', 'thanks', 'sent', 'submitted',
                'відправлено', 'дякуємо', 'успішно'
            ]
            error_indicators = ['error', 'failed', 'invalid', 'помилка']
            
            has_success = any(indicator in page_source for indicator in success_indicators)
            has_error = any(indicator in page_source for indicator in error_indicators)
            
            if has_success and not has_error:
                test_result["status"] = "success"
                test_result["message"] = "Contact form submitted successfully and success message found."
            elif has_error:
                test_result["status"] = "failed"
                test_result["message"] = "Contact form submitted, but error message found."
            else:
                test_result["status"] = "unknown"
                test_result["message"] = "Contact form submitted, but no clear success/error message found."

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
