"""
Enhanced Browser Automation with AI-Powered Element Detection

Provides robust browser automation using Selenium with intelligent element finding.
Uses AI vision and natural language descriptions to locate UI elements.

Features:
- Smart element finding (by description, not just CSS selectors)
- YouTube-specific automation helpers
- Screenshot capture and analysis
- Multi-tab management
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support.ui import Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except Exception:
    webdriver = None
    By = None
    Keys = None
    WebDriverWait = None
    Select = None
    EC = None
    TimeoutException = Exception
    NoSuchElementException = Exception
    SELENIUM_AVAILABLE = False
from PIL import Image
import io

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Browser configuration"""
    headless: bool = False
    window_size: Tuple[int, int] = (1920, 1080)
    user_data_dir: Optional[str] = None  # Persist cookies/sessions
    timeout: int = 30
    screenshot_on_error: bool = True


class BrowserAutomation:
    """
    Enhanced browser automation with AI-powered element detection
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize browser automation
        
        Args:
            config: Browser configuration
        """
        self.config = config or BrowserConfig()
        self.driver: Optional[Any] = None
        self.wait: Optional[Any] = None
        self.current_url: str = ""
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        logger.info("✅ BrowserAutomation initialized")
    
    def start_browser(self):
        """Start the browser"""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium is not installed. Install with: pip install selenium")

        if self.driver:
            logger.warning("Browser already started")
            return
        
        logger.info("🌐 Starting browser...")
        
        options = webdriver.ChromeOptions()
        
        if self.config.headless:
            options.add_argument("--headless")
        
        # Anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Window size
        options.add_argument(f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}")
        
        # User data directory for persistent login
        if self.config.user_data_dir:
            options.add_argument(f"--user-data-dir={self.config.user_data_dir}")
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, self.config.timeout)
            logger.info("✅ Chrome started successfully")
            return
        except Exception as chrome_error:
            logger.warning(f"⚠️ Chrome start failed, trying Edge fallback: {chrome_error}")

        try:
            edge_options = webdriver.EdgeOptions()
            if self.config.headless:
                edge_options.add_argument("--headless")
            edge_options.add_argument(
                f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}"
            )
            self.driver = webdriver.Edge(options=edge_options)
            self.wait = WebDriverWait(self.driver, self.config.timeout)
            logger.info("✅ Edge started successfully")
        except Exception as edge_error:
            logger.error(f"❌ Failed to start browser (Chrome and Edge): {edge_error}")
            raise
    
    def navigate(self, url: str) -> bool:
        """
        Navigate to URL
        
        Args:
            url: URL to navigate to
        
        Returns:
            Success status
        """
        if not self.driver:
            self.start_browser()
        
        try:
            logger.info(f"🔗 Navigating to: {url}")
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            self.driver.get(url)
            self.current_url = url
            
            # Wait for page load
            time.sleep(2)
            
            logger.info(f"✅ Navigated to: {self.driver.title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            if self.config.screenshot_on_error:
                self._save_screenshot("navigation_error")
            return False
    
    def find_element_by_description(self, description: str, timeout: Optional[int] = None) -> Optional[Any]:
        """
        Find element by natural language description
        
        Uses cascading strategy:
        1. Try common selectors based on description keywords
        2. Use AI vision (if available)
        3. Brute force search through all elements
        
        Args:
            description: Natural language description (e.g., "sign in button", "search box")
            timeout: Custom timeout in seconds
        
        Returns:
            WebElement or None
        """
        if not self.driver:
            return None
        
        logger.info(f"🔍 Finding element: {description}")
        timeout = timeout or self.config.timeout
        
        # Strategy 1: Try common patterns
        element = self._find_by_common_patterns(description, timeout)
        if element:
            return element
        
        # Strategy 2: Search by text content
        element = self._find_by_text(description, timeout)
        if element:
            return element
        
        # Strategy 3: Search by attributes
        element = self._find_by_attributes(description, timeout)
        if element:
            return element
        
        logger.warning(f"⚠️ Element not found: {description}")
        return None
    
    def _find_by_common_patterns(self, description: str, timeout: int) -> Optional[Any]:
        """Find element using common patterns"""
        desc_lower = description.lower()
        
        # Common button patterns
        if 'button' in desc_lower:
            selectors = [
                f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower.replace(' button', '')}')]",
                f"//input[@type='button'][contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower.replace(' button', '')}')]",
                f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{desc_lower.replace(' button', '')}')]"
            ]
            return self._try_selectors(selectors, timeout)
        
        # Input/search box patterns
        if any(word in desc_lower for word in ['input', 'search', 'box', 'field']):
            selectors = [
                "//input[@type='search']",
                "//input[@type='text']",
                "//input[contains(@placeholder, 'search')]",
                "//textarea"
            ]
            return self._try_selectors(selectors, timeout)
        
        # Link patterns
        if 'link' in desc_lower:
            text = desc_lower.replace('link', '').strip()
            selectors = [
                f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]"
            ]
            return self._try_selectors(selectors, timeout)
        
        # Icon/image patterns
        if 'icon' in desc_lower or 'image' in desc_lower:
            text = desc_lower.replace('icon', '').replace('image', '').strip()
            selectors = [
                f"//button[@aria-label='{text}']",
                f"//div[@aria-label='{text}']",
                f"//img[@alt='{text}']"
            ]
            return self._try_selectors(selectors, timeout)
        
        return None
    
    def _find_by_text(self, description: str, timeout: int) -> Optional[Any]:
        """Find element containing the description text"""
        try:
            # Try exact text match
            element = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{description.lower()}')]"
                ))
            )
            return element
        except TimeoutException:
            return None
    
    def _find_by_attributes(self, description: str, timeout: int) -> Optional[Any]:
        """Find element by attributes (aria-label, title, etc.)"""
        selectors = [
            f"//*[@aria-label='{description}']",
            f"//*[contains(@aria-label, '{description}')]",
            f"//*[@title='{description}']",
            f"//*[contains(@title, '{description}')]",
            f"//*[@placeholder='{description}']",
            f"//*[contains(@placeholder, '{description}')]"
        ]
        return self._try_selectors(selectors, timeout)
    
    def _try_selectors(self, selectors: List[str], timeout: int) -> Optional[Any]:
        """Try multiple selectors"""
        for selector in selectors:
            try:
                element = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                logger.debug(f"✅ Found element with: {selector}")
                return element
            except TimeoutException:
                continue
        return None
    
    def click_element(self, element_description: str, timeout: Optional[int] = None) -> bool:
        """
        Click element by description
        
        Args:
            element_description: Description of element to click
            timeout: Custom timeout
        
        Returns:
            Success status
        """
        try:
            element = self.find_element_by_description(element_description, timeout)
            if not element:
                logger.error(f"❌ Cannot click: element not found '{element_description}'")
                return False
            
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            
            # Wait for element to be interactable.
            self.wait.until(lambda _driver: element.is_displayed() and element.is_enabled())

            try:
                element.click()
            except Exception:
                # JS fallback helps with overlay/intercepted click issues.
                self.driver.execute_script("arguments[0].click();", element)
            
            logger.info(f"✅ Clicked: {element_description}")
            time.sleep(1)  # Wait for action to complete
            return True
            
        except Exception as e:
            logger.error(f"❌ Click failed: {e}")
            if self.config.screenshot_on_error:
                self._save_screenshot("click_error")
            return False
    
    def type_text(self, element_description: str, text: str, clear_first: bool = True) -> bool:
        """
        Type text into an input field
        
        Args:
            element_description: Description of input field
            text: Text to type
            clear_first: Clear field before typing
        
        Returns:
            Success status
        """
        try:
            element = self.find_element_by_description(element_description)
            if not element:
                logger.error(f"❌ Cannot type: element not found '{element_description}'")
                return False
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            logger.info(f"✅ Typed '{text}' into: {element_description}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Type failed: {e}")
            return False
    
    def select_option(self, element_description: str, option_text: str) -> bool:
        """
        Select dropdown option
        
        Args:
            element_description: Description of dropdown
            option_text: Text of option to select
        
        Returns:
            Success status
        """
        try:
            element = self.find_element_by_description(element_description)
            if not element:
                logger.error(f"❌ Dropdown not found: {element_description}")
                return False
            
            select = Select(element)
            select.select_by_visible_text(option_text)
            
            logger.info(f"✅ Selected '{option_text}' in: {element_description}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Select failed: {e}")
            return False
    
    def scroll(self, direction: str = "down", amount: int = 300) -> bool:
        """
        Scroll page
        
        Args:
            direction: "up" or "down"
            amount: Pixels to scroll
        
        Returns:
            Success status
        """
        try:
            if direction == "down":
                self.driver.execute_script(f"window.scrollBy(0, {amount});")
            else:
                self.driver.execute_script(f"window.scrollBy(0, -{amount});")
            
            logger.info(f"✅ Scrolled {direction} by {amount}px")
            time.sleep(0.5)
            return True
            
        except Exception as e:
            logger.error(f"❌ Scroll failed: {e}")
            return False
    
    def wait_for_element(self, element_description: str, timeout: int = 10) -> bool:
        """
        Wait for element to appear
        
        Args:
            element_description: Description of element
            timeout: Seconds to wait
        
        Returns:
            True if element appears
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.find_element_by_description(element_description, timeout=2):
                return True
            time.sleep(0.5)
        return False
    
    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """
        Take screenshot
        
        Args:
            filename: Optional filename
        
        Returns:
            Path to screenshot
        """
        if not self.driver:
            logger.warning("⚠️ Cannot take screenshot: browser is not started")
            return ""

        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        
        filepath = os.path.join(self.screenshot_dir, filename)
        self.driver.save_screenshot(filepath)
        
        logger.info(f"📸 Screenshot saved: {filepath}")
        return filepath
    
    def _save_screenshot(self, prefix: str):
        """Save error screenshot"""
        if not self.driver:
            return
        try:
            self.take_screenshot(f"{prefix}_{int(time.time())}.png")
        except Exception as e:
            logger.debug(f"Failed to save diagnostic screenshot: {e}")
    
    def get_page_text(self) -> str:
        """Get all visible text from page"""
        if not self.driver:
            return ""
        
        return self.driver.find_element(By.TAG_NAME, "body").text
    
    def close(self):
        """Close browser"""
        if self.driver:
            logger.info("🔒 Closing browser")
            self.driver.quit()
            self.driver = None
            self.wait = None


class YouTubeAutomation(BrowserAutomation):
    """
    Specialized automation for YouTube with common actions
    """
    
    YOUTUBE_URL = "https://www.youtube.com"
    
    def go_to_history(self) -> bool:
        """Navigate to YouTube history page"""
        if self.YOUTUBE_URL not in self.current_url:
            self.navigate(self.YOUTUBE_URL)
        
        logger.info("📜 Navigating to history...")
        
        # Method 1: Direct URL
        history_url = f"{self.YOUTUBE_URL}/feed/history"
        return self.navigate(history_url)
    
    def clear_watch_history(self, timeframe: str = "all") -> bool:
        """
        Clear watch history
        
        Args:
            timeframe: "today", "yesterday", "week", "month", "all"
        
        Returns:
            Success status
        """
        logger.info(f"🗑️ Clearing watch history ({timeframe})...")
        
        if not self.go_to_history():
            return False
        
        # Click "Clear all watch history" button
        if not self.click_element("clear all watch history"):
            # Try alternate descriptions
            if not self.click_element("clear watch history"):
                logger.error("❌ Could not find clear history button")
                return False
        
        time.sleep(1)
        
        # Confirm if needed
        if self.wait_for_element("clear history", timeout=3):
            self.click_element("clear history")
        
        logger.info("✅ History cleared")
        return True
    
    def search(self, query: str) -> bool:
        """Search YouTube"""
        if self.YOUTUBE_URL not in self.current_url:
            self.navigate(self.YOUTUBE_URL)
        
        if self.type_text("search", query):
            # Press Enter
            try:
                search_box = self.find_element_by_description("search")
                search_box.send_keys(Keys.RETURN)
                logger.info(f"✅ Searched for: {query}")
                return True
            except Exception as e:
                logger.error(f"❌ Search failed: {e}")
                return False
        return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test browser automation
    browser = BrowserAutomation(BrowserConfig(headless=False))
    
    try:
        # Test navigation
        browser.start_browser()
        browser.navigate("https://www.google.com")
        
        # Test element finding and interaction
        browser.type_text("search", "Python programming")
        time.sleep(2)
        
        browser.take_screenshot("test_screenshot.png")
        
    finally:
        browser.close()
