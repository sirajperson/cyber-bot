import time
import logging
from typing import Type, Optional
from pydantic import BaseModel, Field, HttpUrl
from bs4 import BeautifulSoup

from crewai.tools import BaseTool

# Import your existing Navigator class
from .....viewers.navigator import Navigator # Adjust path if necessary

logger = logging.getLogger(__name__)

# --- Pydantic Input Schema ---
class NavigatorToolInput(BaseModel):
    """Input schema for the NavigatorTool."""
    url: str = Field(..., description="The fully qualified URL to navigate to (e.g., 'https://example.com').")

# --- Tool Definition ---
class NavigatorTool(BaseTool):
    name: str = "Headless Browser Navigator"
    description: str = (
        "Navigates to a given URL using a headless browser (Selenium Chromium) "
        "and returns the page's final URL, title, source HTML (snippet), simplified text content (snippet), "
        "and a base64 encoded screenshot. Useful for accessing web pages, analyzing content, "
        "and getting a visual representation."
    )
    args_schema: Type[BaseModel] = NavigatorToolInput
    navigator_instance: Optional[Navigator] = None # To hold the browser instance

    def _run(self, url: str) -> str:
        """Navigates to the URL and gathers page data."""
        nav = None # Initialize nav to None for finally block
        max_content_length = 5000 # Max characters for source/text snippets

        try:
            logger.info(f"NavigatorTool: Initializing browser for URL: {url}")
            # Initialize Navigator (uses default headless options from your class)
            # We create a new instance for each run to ensure isolation
            nav = Navigator()

            logger.info(f"NavigatorTool: Navigating to {url}")
            nav.navigate_to(url)
            # Give page a moment to potentially load dynamic content
            time.sleep(3) # Adjust sleep time as needed

            # Gather data
            final_url = nav.get_current_url()
            title = nav.get_title()
            page_source = nav.get_page_source()
            screenshot_base64 = nav.get_screenshot_as_base64()

            # Get simplified text content
            soup = BeautifulSoup(page_source, "html.parser")
            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            text_content = soup.get_text(separator=" ", strip=True)

            logger.info(f"NavigatorTool: Data gathered successfully for {final_url}")

            # Truncate long content
            source_snippet = page_source[:max_content_length] + "..." if len(page_source) > max_content_length else page_source
            text_snippet = text_content[:max_content_length] + "..." if len(text_content) > max_content_length else text_content
            screenshot_snippet = screenshot_base64[:100] + "..." # Just show a snippet of base64

            # Format the output string
            output = (
                f"--- Navigation Result for: {url} ---\n"
                f"Final URL: {final_url}\n"
                f"Page Title: {title}\n\n"
                f"--- Page Text Content (Snippet) ---\n"
                f"{text_snippet}\n\n"
                f"--- Page Source HTML (Snippet) ---\n"
                f"```html\n{source_snippet}\n```\n\n"
                f"--- Screenshot (Base64 Snippet) ---\n"
                f"{screenshot_snippet}\n"
                f"--- End of Navigation Result ---"
            )
            return output

        except Exception as e:
            logger.error(f"NavigatorTool: Error during navigation to {url}: {e}", exc_info=True)
            return f"Error navigating to {url}: {e}"
        finally:
            # Ensure browser is closed even if errors occur
            if nav:
                try:
                    logger.info("NavigatorTool: Closing browser instance.")
                    nav.close_browser()
                except Exception as close_err:
                    logger.error(f"NavigatorTool: Error closing browser: {close_err}", exc_info=True)

# Example usage (for local testing)
if __name__ == "__main__":
    nav_tool = NavigatorTool()

    print("\n--- Testing Navigation Tool ---")
    test_url = "https://example.com" # A simple, fast-loading site
    result = nav_tool.run(url=test_url)
    print(result)

    print("\n--- Testing Invalid URL ---")
    invalid_url = "invalid-url-format"
    result_invalid = nav_tool.run(url=invalid_url)
    print(result_invalid)

    print("\n--- Testing Non-existent URL ---")
    non_existent_url = "http://thissitedoesnotexist12345abc.com"
    result_nonexist = nav_tool.run(url=non_existent_url)
    print(result_nonexist)
