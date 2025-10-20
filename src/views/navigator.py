import re
import unicodedata
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import Callable, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromiumService
from webdriver_manager.core.os_manager import ChromeType

import random
import time
import logging
import subprocess

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for sleep times and timeouts
MIN_SLEEP_TIME = 1
MAX_SLEEP_TIME = 3
UI_TIME_OUT = 10

class HelpFunctions:
    def __init__(self):
        pass

    def get_base_url(self, url):
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    def generate_excerpt(self, content, max_length=200):
        return content[:max_length] + "..." if len(content) > max_length else content

    def format_text(self, original_text):
        soup = BeautifulSoup(original_text, "html.parser")
        formatted_text = soup.get_text(separator=" ", strip=True)
        formatted_text = unicodedata.normalize("NFKC", formatted_text)
        formatted_text = re.sub(r"\s+", " ", formatted_text)
        formatted_text = formatted_text.strip()
        formatted_text = self.remove_emojis(formatted_text)
        return formatted_text

    def remove_emojis(self, text):
        return "".join(c for c in text if not unicodedata.category(c).startswith("So"))

    def truncate_to_n_words(self, text, word_limit):
        tokens = text.split()
        truncated_tokens = tokens[:word_limit]
        return " ".join(truncated_tokens)

class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Any] = None):
        self.event_emitter = event_emitter

    async def emit(self, description="Unknown State", status="in_progress", done=False):
        if self.event_emitter:
            event_data = {
                "type": "status",
                "data": {
                    "status": status,
                    "description": description,
                    "done": done,
                },
            }
            if asyncio.iscoroutinefunction(self.event_emitter):
                await self.event_emitter(event_data)
            else:
                self.event_emitter(event_data)
class Navigator:
    """Controls the ChromeDriver and allows you to drive the browser with authentication support."""
    def __init__(
        self,
        options: ChromeOptions = None,
        service: ChromeService = None,
        keep_alive: bool = True,
        cookies: list[dict] = None,
    ) -> None:
        self.USER_AGENT = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
        if options is None:
            options = ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("window-size=1920,1080")
            options.add_argument("--disable-extensions")
            options.add_argument("--dns-prefetch-disable")
            options.add_argument(f"user-agent={self.USER_AGENT}")

        if cookies:
            for cookie in cookies:
                self.add_cookie(cookie)

        # Initialize WebDriver
        self.driver = webdriver.Chrome(service=ChromiumService(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()))
        self.driver.set_page_load_timeout(30)
        self.help_functions = HelpFunctions()
        logger.info("Navigator initialized")

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the provided credentials."""
        try:
            self.navigate_to("https://cyberskyline.com/competition/dashboard")
            time.sleep(2)  # Wait for page load

            # Use NAME selectors for inputs
            username_field = self.wait_for_element_to_be_clickable(By.NAME, "login", timeout=10)
            password_field = self.wait_for_element_to_be_clickable(By.NAME, "password", timeout=10)

            if username_field and password_field:
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)

                # Click "Sign in" button (use text or class)
                signin_button = self.wait_for_element_to_be_clickable(By.XPATH, "//button[contains(text(), 'Sign in')]",
                                                                      timeout=10)
                if signin_button:
                    signin_button.click()
                else:
                    # Fallback: click by class
                    self.click_element(By.CSS_SELECTOR, "button.ui.blue.large.fluid.button")

                time.sleep(3)  # Wait for login

                if "dashboard" in self.get_current_url():
                    logger.info("Authentication successful")
                    return True
                logger.warning("Authentication may have failed")
            else:
                logger.error("Login fields not found")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False


    def navigate_to(self, url: str):
        """Navigate to the specified URL."""
        logger.info(f"Navigating to {url}")
        self.driver.get(url)

    def get_page_source(self) -> str:
        """Get the page source of the current page."""
        return self.driver.page_source

    def get_current_url(self) -> str:
        """Get the current URL."""
        return self.driver.current_url

    def get_title(self) -> str:
        """Get the title of the current page."""
        return self.driver.title

    def find_element(self, by: str, value: str) -> Optional[Any]:
        """Find an element on the page."""
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None

    def find_elements(self, by: str, value: str) -> list:
        """Find multiple elements on the page."""
        return self.driver.find_elements(by, value)

    def click_element(self, by: str, value: str) -> bool:
        """Click on an element specified by a selector."""
        element = self.find_element(by, value)
        if element:
            element.click()
            return True
        return False

    def send_keys_to_element(self, by: str, value: str, keys: str) -> bool:
        """Send keys to an element."""
        element = self.find_element(by, value)
        if element:
            element.send_keys(keys)
            return True
        return False

    def execute_script(self, script: str, *args):
        """Execute JavaScript in the context of the current page."""
        return self.driver.execute_script(script, *args)

    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_to_element(self, by: str, value: str) -> bool:
        """Scroll to a specific element on the page."""
        element = self.find_element(by, value)
        if element:
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
            return True
        return False

    def take_screenshot(self, file_path: str):
        """Take a screenshot of the current page."""
        self.driver.save_screenshot(file_path)

    def switch_to_frame(self, frame_reference):
        """Switch to a frame using its name, ID, index, or WebElement."""
        self.driver.switch_to.frame(frame_reference)

    def switch_to_default_content(self):
        """Switch back to the default content."""
        self.driver.switch_to.default_content()

    def back(self):
        """Navigate back in the browser history."""
        self.driver.back()

    def forward(self):
        """Navigate forward in the browser history."""
        self.driver.forward()

    def refresh(self):
        """Refresh the current page."""
        self.driver.refresh()

    def accept_alert(self) -> bool:
        """Accept a JavaScript alert."""
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
            return True
        except Exception:
            return False

    def dismiss_alert(self) -> bool:
        """Dismiss a JavaScript alert."""
        try:
            alert = self.driver.switch_to.alert
            alert.dismiss()
            return True
        except Exception:
            return False

    def get_cookies(self):
        """Get all cookies."""
        return self.driver.get_cookies()

    def add_cookie(self, cookie_dict):
        """Add a cookie."""
        self.driver.add_cookie(cookie_dict)

    def delete_cookie(self, name: str):
        """Delete a cookie by name."""
        self.driver.delete_cookie(name)

    def delete_all_cookies(self):
        """Delete all cookies."""
        self.driver.delete_all_cookies()

    def wait_for_element(self, by: str, value: str, timeout=10) -> Optional[Any]:
        """Wait for an element to be present on the page."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def close_browser(self):
        """Close the browser and quit the driver."""
        logger.info("Closing browser")
        self.driver.quit()

    def maximize_window(self):
        """Maximize the browser window."""
        self.driver.maximize_window()

    def minimize_window(self):
        """Minimize the browser window."""
        self.driver.minimize_window()

    def set_window_size(self, width: int, height: int):
        """Set the browser window size."""
        self.driver.set_window_size(width, height)

    def get_screenshot_as_base64(self):
        """Get a screenshot of the current page as a base64-encoded string."""
        return self.driver.get_screenshot_as_base64()

    def clear_cookies(self):
        """Clear all cookies."""
        self.driver.delete_all_cookies()

    def switch_to_new_window(self):
        """Switch focus to a new window or tab."""
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def close_current_tab(self):
        """Close the current browser tab."""
        self.driver.close()

    def is_element_present(self, by: str, value: str) -> bool:
        """Check if an element is present on the page."""
        return self.find_element(by, value) is not None

    def wait_for_element_to_be_clickable(self, by: str, value: str, timeout=10) -> Optional[Any]:
        """Wait for an element to be clickable."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            return None

    def get_element_text(self, by: str, value: str) -> str:
        """Get text content of an element."""
        element = self.find_element(by, value)
        return element.text if element else ""

    def get_element_attribute(self, by: str, value: str, attribute: str) -> str:
        """Get an attribute value of an element."""
        element = self.find_element(by, value)
        return element.get_attribute(attribute) if element else ""

    def hover_over_element(self, by: str, value: str) -> bool:
        """Hover over an element."""
        from selenium.webdriver.common.action_chains import ActionChains
        element = self.find_element(by, value)
        if element:
            action = ActionChains(self.driver)
            action.move_to_element(element).perform()
            return True
        return False

    def random_sleep(self, min_sleep: int = MIN_SLEEP_TIME, max_sleep: int = MAX_SLEEP_TIME):
        """Pause execution for a random amount of time."""
        sleep_time = random.uniform(min_sleep, max_sleep)
        time.sleep(sleep_time)

    def click_with_js(
        self,
        click_element_id: str,
        wait_element_id: str,
        by: str = By.ID,
        min_sleep: int = MIN_SLEEP_TIME,
        max_sleep: int = MAX_SLEEP_TIME,
        time_out: int = UI_TIME_OUT,
    ):
        """
        Click an element using JavaScript and wait for another element to appear.
        """
        try:
            element = self.find_element(by, click_element_id)
            if element:
                self.execute_script("arguments[0].click();", element)
                WebDriverWait(self.driver, time_out).until(
                    EC.visibility_of_element_located((by, wait_element_id))
                )
                self.random_sleep(min_sleep, max_sleep)
            else:
                raise NoSuchElementException(
                    f"Element with {by}='{click_element_id}' not found."
                )
        except Exception as e:
            logger.error(f"JS click error: {str(e)}")
            raise

    def iframe_search(self, by: str = By.ID, search_tag: str = "") -> Optional[Any]:
        """
        Recursively search for an element by ID within iframes.
        """
        if not search_tag:
            raise ValueError("Invalid Search Term.")
        element = self.find_element(by, search_tag)
        if element:
            return element
        iframes = self.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            self.driver.switch_to.frame(iframe)
            result = self.iframe_search(by, search_tag)
            if result:
                return result
            self.driver.switch_to.parent_frame()
        return None

# Example event emitter function (can be replaced with actual implementation)
async def event_emitter(event_data: dict):
    logger.info(f"Event: {event_data}")