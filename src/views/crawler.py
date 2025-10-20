import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Set, Optional, List

import logging
import time
import json
import re
import os
from dataclasses import dataclass, asdict

from src.models.crawler_interface import CrawlerInterface
from src.views.navigator import Navigator
from src.common.config import Config
from src.common.openrouter_api import OpenRouterAPI
import asyncio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class ModuleData:
    """Structure for module-specific data."""
    name: str
    objectives: str
    questions_markdown: str
    download_urls: List[str]
    screenshot_path: str  # Added to store screenshot path for VLM

class MarkdownResults:
    """Represents a simple data container for storing page title and markdown-like content."""
    def __init__(self, title: str, markdown: str):
        self.title = title
        self.markdown = markdown

    def __str__(self):
        return f"""
{self.title}

{self.markdown}
"""

class WebCrawler(CrawlerInterface):
    """
    A view tool for crawling CyberSkyline Gymnasium, implementing CrawlerInterface to gather
    module data and screenshots for VLM processing.
    """

    def __init__(self, base_url: str, max_depth: int = 3, max_workers: int = 4, navigator: Navigator = None):
        """
        :param base_url: The starting URL for the crawl (e.g., CyberSkyline dashboard).
        :param max_depth: Maximum depth of recursive crawling.
        :param max_workers: Number of threads for concurrent crawling.
        :param navigator: An optional external Navigator instance.
        """
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.SLEEP_TIME = 2
        self.visited: Set[str] = set()
        self.url_map: Dict[str, List[str]] = defaultdict(list)
        self.html_map: Dict[str, str] = {}
        self.markdown_map: Dict[str, MarkdownResults] = {}
        self.module_data: Dict[str, ModuleData] = {}
        self.screenshot_map: Dict[str, str] = {}  # Store screenshot paths
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.openrouter = OpenRouterAPI()

        # Thread-safe locks
        self.visited_lock = threading.Lock()
        self.map_lock = threading.Lock()
        self.module_lock = threading.Lock()

        self.navigator = navigator
        # Initialize Navigator
        if navigator is None:
            self.navigator = Navigator()
            self.navigator.authenticate(Config.USERNAME, Config.PASSWORD)

    def clean_url(self, url: str) -> str:
        """Remove fragments and normalize URL structure."""
        try:
            parsed = urlparse(url)
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean += f"?{parsed.query}"
            return clean
        except Exception:
            return url

    def is_valid_url(self, url: str) -> bool:
        """Check if the URL is valid for crawling, allowing module-related paths."""
        try:
            parsed = urlparse(url)
            if not parsed.netloc or parsed.netloc != self.base_domain:
                return False
            path = parsed.path.lower()
            skip_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.css', '.js'}
            if any(path.endswith(ext) for ext in skip_extensions):
                return False
            skip_patterns = {'/wp-admin/', '/wp-includes/', '/feed/', '/xmlrpc.php'}
            if any(pattern in path for pattern in skip_patterns):
                return False
            if '/world/' in path or '/module/' in path:
                return True
            return True
        except Exception:
            return False

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Extract valid links from the page content, focusing on module links."""
        links = set()
        try:
            for link in soup.find_all('a', href=True):
                href = link['href']
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                try:
                    full_url = self.clean_url(urljoin(base_url, href))
                    if self.is_valid_url(full_url):
                        links.add(full_url)
                except Exception as e:
                    logger.error(f"Error processing link {href} in {base_url}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error extracting links from {base_url}: {e}", exc_info=True)
        logger.debug(f"Extracted {len(links)} links from {base_url}")
        return links

    async def extract_module_data(self, soup: BeautifulSoup, url: str, screenshot_path: str) -> ModuleData:
        """Asynchronously extract module data using VLM with screenshot."""
        try:
            html_content = str(soup)
            questions_markdown = await self.openrouter.convert_to_markdown(html_content, screenshot_path)
            download_urls = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith(('.pdf', '.zip'))]

            # Enhanced VLM parsing with fallback
            objectives_match = re.search(r"Objectives:\s*(.*?)(?:\n|$)", questions_markdown, re.DOTALL)
            objectives = objectives_match.group(1).strip() if objectives_match else soup.find('div', class_='objectives').get_text(strip=True) if soup.find('div', class_='objectives') else "No objectives found"
            name = soup.find('h1').get_text(strip=True) if soup.find('h1') else url.split('/')[-1]

            return ModuleData(name=name, objectives=objectives, questions_markdown=questions_markdown, download_urls=download_urls, screenshot_path=screenshot_path)
        except Exception as e:
            logger.error(f"Error extracting module data from {url}: {e}", exc_info=True)
            return ModuleData(name=url.split('/')[-1], objectives="", questions_markdown="", download_urls=[], screenshot_path=screenshot_path)

    def crawl(self, url: Optional[str] = None, depth: Optional[int] = None) -> None:
        """Recursively crawl starting from the given URL, taking screenshots for VLM."""
        if url is None:
            url = self.base_url
        if depth is None:
            depth = self.max_depth

        url = self.clean_url(urljoin(self.base_url, url))

        with self.visited_lock:
            if url in self.visited or depth == 0:
                logger.debug(f"Already visited {url} or depth=0, skipping")
                return

        try:
            start_time = time.time()
            logger.info(f"Crawling {url}")

            self.navigator.navigate_to(url)
            html_content = self.navigator.get_page_source()
            load_time_ms = int((time.time() - start_time) * 1000)

            if not html_content:
                logger.warning(f"No HTML content received for {url}")
                return

            soup = BeautifulSoup(html_content, 'html.parser')
            site_markdown = soup.text

            # Take screenshot for VLM
            screenshot_path = f"data/screenshots/{url.replace('/', '_').strip('_')}_screenshot.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            self.navigator.take_screenshot(screenshot_path)

            with self.map_lock:
                self.html_map[url] = html_content
                self.markdown_map[url] = MarkdownResults(soup.title.string if soup.title else "", site_markdown)
                extracted_links = self.extract_links(soup, url)
                self.url_map[url] = list(extracted_links)
                self.screenshot_map[url] = screenshot_path

            if self._determine_page_type(soup, url) == 'module':
                with self.module_lock:
                    # Use async execution for module data extraction
                    loop = asyncio.get_event_loop()
                    self.module_data[url] = loop.run_until_complete(self.extract_module_data(soup, url, screenshot_path))

            if depth > 1:
                futures = []
                for link_url in extracted_links:
                    with self.visited_lock:
                        if link_url not in self.visited:
                            future = self.executor.submit(self.crawl, link_url, depth - 1)
                            futures.append(future)

                for future in futures:
                    try:
                        future.result(timeout=30)
                    except TimeoutError:
                        logger.error(f"Timeout while crawling child page of {url}")
                    except Exception as e:
                        logger.error(f"Error in child crawl of {url}: {str(e)}", exc_info=True)

            with self.visited_lock:
                self.visited.add(url)
                logger.debug(f"Visiting {url}, depth {depth}")

        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {str(e)}", exc_info=True)

    def get_results(self) -> Dict:
        """Return all accumulated data, implementing CrawlerInterface."""
        return {
            "base_url": self.base_url,
            "pages_crawled": len(self.visited),
            "url_map": dict(self.url_map),
            "html_content": self.html_map,
            "markdown_map": self.markdown_map,
            "module_data": {url: asdict(data) for url, data in self.module_data.items()},
            "screenshot_map": self.screenshot_map,
            "statistics": {
                "total_links": sum(len(links) for links in self.url_map.values()),
                "unique_pages": len(self.visited),
                "domain": self.base_domain,
            }
        }

    def close(self) -> None:
        """Clean up resources, implementing CrawlerInterface."""
        logger.info("Shutting down crawler...")
        self.executor.shutdown(wait=True)
        if self.own_navigator:
            try:
                self.navigator.close_browser()
            except Exception as e:
                logger.error(f"Error closing Navigator: {e}", exc_info=True)

    def crawl_site(self, url: str, max_depth: int = 3, max_workers: int = 4) -> Dict:
        """Asynchronously crawl a site and return comprehensive data."""
        try:
            self.max_depth = max_depth
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
            asyncio.to_thread(self.crawl)  # Run synchronous crawl in a thread
            results = self.get_results()
            self.close()
            logger.info(f"Completed crawl for {url}")
            return results
        except Exception as e:
            logger.error(f"Crawler failed for {url}: {e}", exc_info=True)
            return {
                "error": str(e), "base_url": url, "pages_crawled": 0, "url_map": {},
                "html_content": {}, "markdown_map": {}, "module_data": {}, "screenshot_map": {},
                "statistics": {}
            }

if __name__ == "__main__":
    import asyncio
    async def main():
        crawler = WebCrawler(Config.BASE_URL)
        results = crawler.crawl_site(Config.BASE_URL, max_depth=3, max_workers=4)
        print(json.dumps(results, indent=2))
    asyncio.run(main())