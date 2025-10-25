import os
import logging
from src.viewers.navigator import Navigator
from src.viewers.crawler import ModuleCrawler
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def crawl_module_thread(module_name: str, module_url: WebElement, index: int, total: int, cookies: list[dict]) -> tuple:
    """Thread function: Create independent WebCrawler with copied login."""
    logging.info(f"[Thread {index}/{total}] Starting: {module_name}")

    # Here we create a new navigation window, and pass the login tokens.
    navigator = Navigator(cookies=cookies)

    # Get the module url.
    # We need to click the link in the new session to navigate
    try:
        module_click_url = module_url.get_attribute('href')
        if not module_click_url:
            raise ValueError("Module link has no href attribute")

        navigator.navigate_to(module_click_url)
        crawl_url = navigator.get_current_url()
        logging.info(f"[Thread {index}/{total}] Navigated to {crawl_url}")

    except Exception as e:
        logging.error(f"[Thread {index}/{total}] Failed to navigate to module {module_name}: {e}")
        # Fallback or error
        crawl_url = module_url.parent.current_url

    # Initialize a module crawler.
    # This crawler will only crawl the *current* page (max_depth=1)
    crawler = ModuleCrawler(
        base_url=crawl_url,  # Use current after navigation
        navigator=navigator,
        max_depth=1,  # Only crawl this specific module page
        max_workers=1
    )

    try:
        # Send the crawler work to complete.
        # It will crawl the page, take a screenshot, and call the VLM
        results = crawler.crawl_site(crawl_url, max_depth=1, max_workers=1)
        # We close the crawler (and its navigator) *within the thread*
        crawler.close()
        logging.info(f"[Thread {index}/{total}] Completed: {module_name}")
        return module_name, results
    except Exception as e:
        logging.error(f"[Thread {index}/{total}] Error crawling {module_name}: {e}")
        if crawler:
            crawler.close()
        return module_name, {"error": str(e)}


class GraphController:

    async def clone_site(self, navigator: Navigator) -> List[tuple]:
        """
        Asynchronously crawls the site to "clone" module data, HTML, and screenshots.
        This function performs all data collection.
        """
        logger.info("Starting site clone (data collection)")

        # Get cookies from the main authenticated session
        cookies = navigator.get_cookies()

        # Extract module links from the main navigator instance
        module_list = navigator.find_element(By.ID, "HopscotchModuleList")
        if not module_list:
            logging.error("HopscotchModuleList not found")
            return []

        module_links = module_list.find_elements(By.TAG_NAME, "a")
        logging.info(f"Found {len(module_links)} modules to clone")

        os.makedirs("data", exist_ok=True)

        crawl_results = []
        try:
            module_futures = []
            # Use ThreadPoolExecutor to run blocking, isolated crawl threads
            executor = ThreadPoolExecutor(max_workers=4)

            for i, link in enumerate(module_links, 1):
                module_name = link.find_element(By.TAG_NAME, "h3").text.strip()

                future = executor.submit(
                    crawl_module_thread,
                    module_name,
                    link,
                    i,
                    len(module_links),
                    cookies
                )
                module_futures.append(future)

            # Wait & collect results as they complete
            for future in as_completed(module_futures):
                module_name, results = future.result()
                crawl_results.append((module_name, results))
                logging.info(f"Collected clone data for {module_name}")

            executor.shutdown()
            logging.info(f"Site cloning (data collection) complete! Collected {len(crawl_results)} modules.")
            return crawl_results

        except Exception as e:
            logger.error(f"Site cloning failed: {str(e)}", exc_info=True)
            return crawl_results  # Return whatever was collected
