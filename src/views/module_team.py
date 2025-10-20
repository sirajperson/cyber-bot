from crewai import Agent, Task
from src.models.agent_interface import AgentInterface
from src.common.openrouter_api import OpenRouterAPI
from src.common.file_handler import FileHandler  # Assume FileHandler implements FileInterface
import logging
import os
from typing import Dict, Any, Optional
import asyncio
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModuleTeam(AgentInterface):
    """
    Module Team agent responsible for processing module data, extracting content (e.g., objectives,
    questions) using vision and text analysis, generating tickets, and supporting navigation analysis.
    This class operates as a view tool, presenting processed module data to the controller.
    """

    def __init__(self):
        """Initialize the Module Team with an agent, OpenRouterAPI, and FileHandler."""
        self.agent = Agent(
            role='Module Processor',
            goal='Extract and process module content from CyberSkyline Gymnasium',
            backstory='An expert in web scraping and content analysis with a focus on cybersecurity challenges.',
            verbose=True,
            tools=[]  # Add tools if needed (e.g., for CrewAI tool integration)
        )
        self.openrouter = OpenRouterAPI()
        self.file_handler = FileHandler()
        logger.info("ModuleTeam initialized")

    async def process_module(self, module_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process module data to extract and format content using vision and text analysis.

        Args:
            module_data (Dict[str, Any]): Dictionary containing module details, including:
                - 'url': The URL of the module page.
                - 'html': The raw HTML content.
                - 'screenshot_path': Optional path to a screenshot for vision analysis.

        Returns:
            Dict[str, Any]: Processed data including:
                - 'name': The module name.
                - 'objectives': The module objectives as text.
                - 'questions_markdown': Markdown representation of questions.
                - 'download_urls': List of downloadable file URLs.

        Raises:
            ValueError: If required module data is missing or invalid.
            AIError: If vision analysis fails.
        """
        try:
            url = module_data.get('url')
            html = module_data.get('html')
            screenshot_path = module_data.get('screenshot_path', f"data/{url.split('/')[-1]}_screenshot.png")

            if not html:
                raise ValueError("HTML content is required for module processing")

            soup = BeautifulSoup(html, 'html.parser')
            module_name = soup.find('h1', class_='module-title').get_text(strip=True) if soup.find('h1', class_='module-title') else url.split('/')[-1]
            objectives = soup.find('div', class_='objectives').get_text(strip=True) if soup.find('div', class_='objectives') else "No objectives found"
            question_frames = soup.find_all('div', class_='question-frame')
            questions_html = "\n".join(frame.prettify() for frame in question_frames) if question_frames else ""
            questions_markdown = await self.openrouter.convert_to_markdown(questions_html, screenshot_path) if questions_html else "No questions found"
            download_urls = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith(('.pdf', '.zip'))]

            # Save raw HTML and markdown for reference
            self.file_handler.save_markdown(html, f"data/{url.split('/')[-1]}_raw.html")
            self.file_handler.save_markdown(questions_markdown, f"data/{url.split('/')[-1]}_questions.md")

            return {
                'name': module_name,
                'objectives': objectives,
                'questions_markdown': questions_markdown,
                'download_urls': download_urls
            }
        except Exception as e:
            logger.error(f"Process module failed for {url}: {str(e)}")
            raise

    def generate_ticket(self, question_data: Dict[str, Any]) -> str:
        """
        Generate a ticket file path and content for a specific question with basic metadata.

        Args:
            question_data (Dict[str, Any]): Dictionary containing question details, including:
                - 'module_name': The name of the module (e.g., "Fencing").
                - 'question_text': The question content or markdown.
                - 'category': The category of the module (e.g., "Cryptography").

        Returns:
            str: Path to the generated ticket file (e.g., "cryptography-fencing-q1.txt").

        Raises:
            IOError: If file creation fails.
            ValueError: If question_data is malformed.
        """
        try:
            module_name = question_data.get('module_name', 'unknown')
            question_text = question_data.get('question_text', 'No question')
            category = question_data.get('category', 'uncategorized')
            ticket_path = f"data/{category}-{module_name}-q1.txt"
            ticket_dir = os.path.dirname(ticket_path) or '.'
            os.makedirs(ticket_dir, exist_ok=True)

            ticket_content = (
                f"Module: {module_name}\n"
                f"Category: {category}\n"
                f"Question: {question_text}\n"
                f"Status: Pending Analysis"
            )

            self.file_handler.save_markdown(ticket_content, ticket_path)
            logger.info(f"Ticket generated at {ticket_path}")
            return ticket_path
        except Exception as e:
            logger.error(f"Generate ticket failed: {str(e)}")
            raise

    async def analyze_navigation(self, image_path: Optional[str] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze an image for navigation purposes using a vision model.

        Args:
            image_path (Optional[str]): Local path to the screenshot image.
            image_url (Optional[str]): URL of the image to analyze.

        Returns:
            Dict[str, Any]: Analysis results including:
                - 'elements': List of detected navigation items (e.g., buttons, text).
                - 'description': Summary of the image content for navigation.

        Raises:
            AIError: If the vision model fails to process the image.
        """
        try:
            return await self.openrouter.analyze_image_for_navigation(image_path, image_url)
        except Exception as e:
            logger.error(f"Analyze navigation failed: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage for testing
    import asyncio

    async def main():
        team = ModuleTeam()
        module_data = {
            'url': 'https://cyberskyline.com/module/example',
            'html': '<h1 class="module-title">Example</h1><div class="objectives">Learn basics</div><div class="question-frame">Q1</div>',
            'screenshot_path': 'data/example_screenshot.png'
        }
        processed_data = await team.process_module(module_data)
        print(f"Processed module: {processed_data}")

        question_data = {
            'module_name': 'Example',
            'question_text': 'Solve Q1',
            'category': 'Cryptography'
        }
        ticket_path = await team.generate_ticket(question_data)
        print(f"Ticket created at: {ticket_path}")

        navigation_data = await team.analyze_navigation(image_path='data/example_screenshot.png')
        print(f"Navigation analysis: {navigation_data}")

    asyncio.run(main())