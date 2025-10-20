import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium.webdriver.remote.webelement import WebElement
from src.common.config import Config
from selenium.webdriver.common.by import By
from src.views.navigator import Navigator
from src.views.crawler import WebCrawler
from src.common.openrouter_api import OpenRouterAPI
import time
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(filename='../logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def crawl_module_thread(module_name: str, module_url: WebElement, index: int, total: int, cookies: list) -> tuple:
    """Thread function: Create independent WebCrawler with copied login."""
    logging.info(f"[Thread {index}/{total}] Starting: {module_name}")
    navigator = Navigator()
    navigator.driver = module_url.parent

    # Clear and apply ALL cookies properly
    crawl_url = module_url.parent.current_url
    crawler = WebCrawler(
        base_url=crawl_url,  # Use current after navigation
        navigator=navigator,
        max_depth=1,
        max_workers=2
    )

    try:
        results = crawler.crawl_site(navigator.get_current_url(), max_depth=1, max_workers=2)
        crawler.close()
        logging.info(f"[Thread {index}/{total}] Completed: {module_name}")
        return module_name, results
    except Exception as e:
        logging.error(f"[Thread {index}/{total}] Error {module_name}: {e}")
        return module_name, {"error": str(e)}

async def main():
    logging.info("Starting Cyber Bot")
    openrouter = OpenRouterAPI()

    try:
        navigator = Navigator()
        navigator.authenticate(Config.USERNAME, Config.PASSWORD)

        # Click Dashboard & Enter
        dashboard_link = navigator.find_element(By.XPATH, "/html/body/div/div/div/div/div/div/div/div[1]/div/a[1]")
        if dashboard_link: dashboard_link.click(); time.sleep(2)

        enter_button = navigator.find_element(By.XPATH,
                                              "/html/body/div/div/div/div/div/div/div/div[2]/div/div[1]/div/div/div/div/div[2]/div/div[4]/a")
        if enter_button: enter_button.click(); time.sleep(3); logging.info("Entered Gymnasium")

        # Get cookies after login
        cookies = navigator.get_cookies()

        # Extract module links
        module_list = navigator.find_element(By.ID, "HopscotchModuleList")
        if not module_list:
            logging.error("HopscotchModuleList not found")
            return

        module_links = module_list.find_elements(By.TAG_NAME, "a")
        logging.info(f"Found {len(module_links)} modules")

        os.makedirs("data", exist_ok=True)

        # Thread pool
        module_futures = []
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

        # Wait & collect
        results_data = []
        for future in as_completed(module_futures):
            module_name, results = future.result()
            results_data.append((module_name, results))

        executor.shutdown()

        # Process results
        with open("data/cyberskyline_mindmap.txt", "w", encoding='utf-8') as f:
            f.write("# CyberSkyline Gymnasium Mindmap\n\n")
            for module_name, results in results_data:
                if "error" in results:
                    f.write(f"\n--- {module_name} [ERROR] ---\n{results['error']}\n")
                else:
                    for url, html in results.get("html_content", {}).items():
                        markdown = await openrouter.convert_to_markdown(html)
                        f.write(f"\n--- {module_name} ---\n{markdown}\n")

        logging.info(f"All {len(results_data)} modules crawled!")

    except Exception as e:
        logging.error("Error: %s", str(e))
    finally:
        navigator.close_browser()
        logging.info("Bot execution completed")


if __name__ == "__main__":
    asyncio.run(main())