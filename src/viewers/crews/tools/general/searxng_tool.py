import os
import requests
import json
from typing import Type, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# --- Environment Variable Loading ---
# Get SearXNG connection details from environment or use defaults
DEFAULT_SXNG_URL = "http://127.0.0.1"
DEFAULT_SXNG_PORT = "8888" # SearXNG default port is often 8888 or 8080

SXNG_URL = os.getenv("SXNG_URL", DEFAULT_SXNG_URL)
SXNG_PORT = os.getenv("SXNG_PORT", DEFAULT_SXNG_PORT)
SEARXNG_BASE_URL = f"{SXNG_URL}:{SXNG_PORT}"

# --- Pydantic Input Schema ---
class SearxngToolInput(BaseModel):
    query: str = Field(..., description="The search query string.")
    max_results: int = Field(5, description="Maximum number of search results to return.")

# --- Tool Definition ---
class SearxngTool(BaseTool):
    name: str = "SearXNG Search"
    description: str = (
        f"Performs a search using a SearXNG instance hosted at {SEARXNG_BASE_URL}. "
        "Returns a summarized list of search results including titles, snippets, and URLs. "
        "Useful for OSINT gathering and general web searches."
    )
    args_schema: Type[BaseModel] = SearxngToolInput

    def _run(self, query: str, max_results: int = 5) -> str:
        """Executes the search query against SearXNG and returns summarized results."""
        if not SXNG_URL or not SXNG_PORT:
            return "Error: SXNG_URL or SXNG_PORT environment variables not set."

        # Construct the query URL for JSON format
        params = {
            'q': query,
            'format': 'json',
            # Add other SearXNG parameters if needed (e.g., 'engines', 'language')
        }
        search_url = f"{SEARXNG_BASE_URL}/search?{urlencode(params)}"
        logger.info(f"Querying SearXNG: {search_url}")

        try:
            # Make the HTTP GET request
            response = requests.get(search_url, timeout=20) # 20-second timeout
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            # Parse the JSON response
            results_data = response.json()

            # Extract and summarize results
            summarized_results = []
            results_list = results_data.get("results", [])

            if not results_list:
                return f"No results found for query: '{query}'"

            for i, result in enumerate(results_list):
                if i >= max_results:
                    break
                title = result.get("title", "No Title")
                snippet = result.get("content", "No Snippet")
                url = result.get("url", "#")
                # Clean up snippet
                snippet = snippet.replace('\n', ' ').strip()
                summarized_results.append(f"{i+1}. Title: {title}\n   Snippet: {snippet}\n   URL: {url}")

            return f"Search results for '{query}':\n\n" + "\n\n".join(summarized_results)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to SearXNG ({search_url}): {e}", exc_info=True)
            return f"Error: Could not connect to SearXNG instance at {SEARXNG_BASE_URL}. Details: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from SearXNG: {e}", exc_info=True)
            # Try to return raw text if JSON fails
            raw_text = response.text[:500] + "..." if len(response.text) > 500 else response.text
            return f"Error: Failed to decode JSON response from SearXNG. Raw response snippet:\n```\n{raw_text}\n```"
        except Exception as e:
            logger.error(f"An unexpected error occurred during SearXNG search: {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"

# Example usage (for local testing)
if __name__ == "__main__":
    # Ensure you have a SearXNG instance running locally or set env vars
    print(f"Testing SearXNG Tool against: {SEARXNG_BASE_URL}")
    search_tool = SearxngTool()

    print("\n--- Test 1: Basic Query ---")
    results1 = search_tool.run(query="CrewAI framework")
    print(results1)

    print("\n--- Test 2: Query with Max Results ---")
    results2 = search_tool.run(query="Kali Linux tools", max_results=3)
    print(results2)

    print("\n--- Test 3: Query likely yielding no results ---")
    results3 = search_tool.run(query="asdfqwerlkjhzxcvbnmpoiuytrewq")
    print(results3)
