from abc import ABC, abstractmethod
from typing import Dict, Optional

class CrawlerInterface(ABC):
    """
    Interface defining the contract for web crawling operations in the Cyber Bot project.
    This interface ensures that any crawling implementation provides methods to navigate
    a website, retrieve results, and manage resources, serving as a blueprint for the
    WebCrawler view tool.
    """

    @abstractmethod
    def crawl(self, url: Optional[str] = None, depth: Optional[int] = None) -> None:
        """
        Recursively crawl the website starting from the given URL up to the specified depth.

        Args:
            url (Optional[str]): The starting URL for the crawl. Defaults to the base URL if None.
            depth (Optional[int]): The maximum depth of recursion. Defaults to the configured max_depth if None.

        Raises:
            ValueError: If the URL is invalid or depth is negative.
            Exception: For unexpected crawling errors (e.g., network issues).
        """
        pass

    @abstractmethod
    def get_results(self) -> Dict:
        """
        Return a dictionary containing all data accumulated during the crawl.

        Returns:
            Dict: A dictionary with keys such as 'base_url', 'pages_crawled', 'url_map',
                  'html_content', 'markdown_map', 'seo_data', 'page_metrics', 'module_data',
                  and 'statistics' reflecting the crawl's findings.

        Raises:
            KeyError: If required data structures are not properly initialized.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Clean up resources, including shutting down the executor and closing the navigator.

        Raises:
            Exception: If resource cleanup (e.g., closing the browser) fails.
        """
        pass