import asyncio
from src.views.crawler import WebCrawler
from src.views.module_team import ModuleTeam
from src.views.research_crew import ResearchCrew
from src.common.utils import generate_mermaid_mindmap
import logging

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphController:
    def __init__(self):
        self.crawler = WebCrawler("https://cyberskyline.com/competition/dashboard")
        self.module_team = ModuleTeam()
        self.research_crew = ResearchCrew()

    def organize_teams(self):
        """Asynchronously organize teams to process modules and generate the mindmap."""
        logger.info("Starting team organization")
        try:
            # Await the asynchronous crawl
            results = self.crawler.crawl_site("https://cyberskyline.com/competition/dashboard")
            url_map = results.get("url_map", {})
            module_data = results.get("module_data", {})

            # Process each module
            for url, data in module_data.items():
                logger.info(f"Processing module at {url}")
                processed_data = self.module_team.process_module(data)
                module_name = processed_data.get('name', url.split('/')[-1])
                questions_markdown = processed_data.get('questions_markdown', '')

                # Parse questions_markdown into individual questions (simple split for now)
                questions = [q.strip() for q in questions_markdown.split('\n') if q.strip()]
                for i, question_text in enumerate(questions, 1):
                    question_data = {
                        'module_name': module_name,
                        'question_text': question_text,
                        'category': next((k for k, v in module_data.items() if v['name'] == module_name), 'uncategorized')
                    }
                    ticket_path = self.module_team.generate_ticket(question_data)
                    self.research_crew.generate_ticket(question_data)  # Optional research ticket
                    logger.info(f"Generated tickets for question {i} at {ticket_path}")

            # Generate and save the mindmap
            mindmap = generate_mermaid_mindmap(url_map)
            with open("data/cyberskyline_mindmap.txt", "w", encoding='utf-8') as f:
                f.write(mindmap)
            logger.info("Team organization and graph generation completed")
        except Exception as e:
            logger.error(f"Team organization failed: {str(e)}", exc_info=True)
            raise

    def run(self):
        """Run the controller by executing the team organization asynchronously."""
        asyncio.run(self.organize_teams())

if __name__ == "__main__":
    controller = GraphController()
    controller.run()