from .crawler import WebCrawler
from .navigator import Navigator
from .openrouter_api import OpenRouterAPI
from .config import Config
import os

def main():
    navigator = Navigator()
    crawler = WebCrawler(Config.BASE_URL)
    openrouter = OpenRouterAPI()

    # Authentication (pseudo-code)
    navigator.navigate_to(Config.BASE_URL)
    # Add login logic here

    # Crawl and process
    crawler.crawl()
    results = crawler.get_results()
    for url, html in results.get("html_content", {}).items():
        markdown = openrouter.convert_to_markdown(html)
        # Process markdown into mind map
        with open("data/cyberskyline_mindmap.txt", "w") as f:
            f.write(markdown)

    navigator.close_browser()

if __name__ == "__main__":
    main()
