import os
import asyncio
import logging
from src.views.module_team import ModuleTeam
from src.views.navigator import Navigator
from src.views.research_crew import ResearchCrew
from src.views.crawler import ModuleCrawler
from src.common.utils import generate_mermaid_mindmap
from src.common.openrouter_api import OpenRouterAPI
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def crawl_module_thread(module_name: str, module_url: WebElement, index: int, total: int, cookies: list[dict]) -> tuple:
    # Process each module
    # CrewAI Implementation
    # for url, data in module_data.items():
    #     logger.info(f"Processing module at {url}")
    #     processed_data = self.module_team.process_module(data)
    #     module_name = processed_data.get('name', url.split('/')[-1])
    #     questions_markdown = processed_data.get('questions_markdown', '')
    #
    #     # Parse questions_markdown into individual questions (simple split for now)
    #     questions = [q.strip() for q in questions_markdown.split('\n') if q.strip()]
    #     for i, question_text in enumerate(questions, 1):
    #         question_data = {
    #             'module_name': module_name,
    #             'question_text': question_text,
    #             'category': next((k for k, v in module_data.items() if v['name'] == module_name), 'uncategorized')
    #         }
    #         ticket_path = self.module_team.generate_ticket(question_data)
    #         self.research_crew.generate_ticket(question_data)  # Optional research ticket
    #         logger.info(f"Generated tickets for question {i} at {ticket_path}")
    #
    # # Generate and save the mindmap
    # mindmap = generate_mermaid_mindmap(url_map)
    # with open("data/cyberskyline_mindmap.txt", "w", encoding='utf-8') as f:
    #     f.write(mindmap)
    # logger.info("Team organization and graph generation completed")


    """Thread function: Create independent WebCrawler with copied login."""
    logging.info(f"[Thread {index}/{total}] Starting: {module_name}")

    # Here we create a new navigation window, and pass the login tokens.
    navigator = Navigator(cookies=cookies)

    # Get the module url.
    navigator.driver = module_url.parent

    # Clear and apply ALL cookies properly
    crawl_url = module_url.parent.current_url

    # Initialize a module crawler.
    # TODO: add depth and worker count to .env
    crawler = ModuleCrawler(
        base_url=crawl_url,  # Use current after navigation
        navigator=navigator,
        max_depth=1,
        max_workers=2
    )

    try:
        # Send the crawler work to complete.
        #TODO: add depth and worker count to .env
        results = crawler.crawl_site(navigator.get_current_url(), max_depth=1, max_workers=4)
        crawler.close()
        logging.info(f"[Thread {index}/{total}] Completed: {module_name}")
        return module_name, results
    except Exception as e:
        logging.error(f"[Thread {index}/{total}] Error {module_name}: {e}")
        return module_name, {"error": str(e)}


class GraphController:
    async def organize_teams(self, navigator: Navigator):
        """Asynchronously organize teams to process modules and generate the mindmap."""
        logger.info("Starting team organization")
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
        openrouter = OpenRouterAPI()

        try:
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

            # Process results. This is super simple right now, Just take the graph and make a big file out of it.
            # This could be much more sophisticated.
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
            logger.error(f"Team organization failed: {str(e)}", exc_info=True)
            raise

    def run(self):
        """Run the controller by executing the team organization asynchronously."""
        asyncio.run(self.organize_teams())

if __name__ == "__main__":
    controller = GraphController()
    controller.run()