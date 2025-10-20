from bs4 import BeautifulSoup
from crewai import Agent, Task
from src.models.agent_interface import AgentInterface
from src.common.openrouter_api import OpenRouterAPI
from src.common.file_handler import FileHandler  # Assume FileHandler implements FileInterface
import logging
import os
from typing import Dict, Any, Optional
import asyncio

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResearchCrew(AgentInterface):
    """
    Research Crew agent responsible for analyzing module questions, generating tickets with
    solution approaches using command-line tools, and supporting navigation analysis using
    vision models. This class operates as a view tool, presenting processed data to the
    controller for orchestration.
    """

    def __init__(self):
        """Initialize the Research Crew with an agent, OpenRouterAPI, and FileHandler."""
        self.agent = Agent(
            role='Research Analyst',
            goal='Analyze module questions and suggest command-line tool-based solutions',
            backstory='A skilled cybersecurity researcher with expertise in penetration testing, '
                      'log analysis, and network forensics.',
            verbose=True,
            tools=[]  # Add tools if needed (e.g., for CrewAI tool integration)
        )
        self.openrouter = OpenRouterAPI()
        self.file_handler = FileHandler()
        logger.info("ResearchCrew initialized")

    async def process_module(self, module_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process module data to extract and analyze content using vision and text analysis.

        Args:
            module_data (Dict[str, Any]): Dictionary containing module details, including:
                - 'url': The URL of the module page.
                - 'html': The raw HTML content.
                - 'screenshot_path': Optional path to a screenshot for vision analysis.

        Returns:
            Dict[str, Any]: Processed data including:
                - 'name': The module name.
                - 'objectives': The module objectives as text (if available).
                - 'analyzed_questions': Number of detected questions.
                - 'analysis': Summary of the analysis.

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

            # Use OpenRouter to analyze HTML and screenshot for questions
            questions_html = "\n".join(frame.prettify() for frame in BeautifulSoup(html, 'html.parser').find_all('div', class_='question-frame'))
            questions_markdown = await self.openrouter.convert_to_markdown(questions_html, screenshot_path) if questions_html else "No questions found"
            question_count = questions_html.count('<div class="question-frame">') if questions_html else 0

            return {
                'name': url.split('/')[-1],
                'objectives': BeautifulSoup(html, 'html.parser').find('div', class_='objectives').get_text(strip=True) if BeautifulSoup(html, 'html.parser').find('div', class_='objectives') else "No objectives found",
                'analyzed_questions': question_count,
                'analysis': f'Processed {question_count} questions: {questions_markdown[:100]}...'  # Truncated for brevity
            }
        except Exception as e:
            logger.error(f"Process module failed: {str(e)}")
            raise

    def generate_ticket(self, question_data: Dict[str, Any]) -> str:
        """
        Generate a ticket file path and content for a specific question with a solution approach.

        Args:
            question_data (Dict[str, Any]): Dictionary containing question details, including:
                - 'module_name': The name of the module (e.g., "Fencing").
                - 'question_text': The question content or markdown.
                - 'category': The category of the module (e.g., "Cryptography").

        Returns:
            str: Path to the generated ticket file (e.g., "cryptography-fencing-q1-research.txt").

        Raises:
            IOError: If file creation fails.
            ValueError: If question_data is malformed.
        """
        try:
            module_name = question_data.get('module_name', 'unknown')
            question_text = question_data.get('question_text', 'No question')
            category = question_data.get('category', 'uncategorized')
            ticket_path = f"data/{category}-{module_name}-q1-research.txt"
            ticket_dir = os.path.dirname(ticket_path) or '.'
            os.makedirs(ticket_dir, exist_ok=True)

            # Enhance tool suggestion with OpenRouter analysis
            tools_suggestion = self._suggest_tools(question_text)
            ticket_content = (
                f"Module: {module_name}\n"
                f"Question: {question_text}\n"
                f"Research: Suggested tools and approach:\n{tools_suggestion}"
            )

            self.file_handler.save_markdown(ticket_content, ticket_path)
            logger.info(f"Ticket generated at {ticket_path}")
            return ticket_path
        except Exception as e:
            logger.error(f"Generate ticket failed: {str(e)}")
            raise

    def _suggest_tools(self, question_text: str) -> str:
        """
        Suggest command-line tools based on question content using a heuristic approach.

        Args:
            question_text (str): The text of the question to analyze.

        Returns:
            str: A string containing suggested tools and approaches.
        """
        suggestions = []
        if 'network' in question_text.lower() or 'traffic' in question_text.lower():
            suggestions.append("Use `tcpdump` or `wireshark` to analyze network packets.")
        elif 'file' in question_text.lower() or 'hidden' in question_text.lower():
            suggestions.append("Use `find`, `grep`, or `strings` to inspect files.")
        elif 'password' in question_text.lower():
            suggestions.append("Use `john` or `hashcat` for password cracking.")
        elif 'log' in question_text.lower():
            suggestions.append("Use `cat` and `grep` to analyze log files.")
        else:
            suggestions.append("Use general tools like `cat`, `ls`, or `man` for initial exploration.")
        return "\n".join(suggestions)

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
        crew = ResearchCrew()
        module_data = {"url": "https://example.com/module", "html": "<div class='question-frame'>Question 1</div>"}
        processed_data = await crew.process_module(module_data)
        print(f"Processed module: {processed_data}")

        question_data = {"module_name": "Fencing", "question_text": "Analyze network traffic", "category": "Cryptography"}
        ticket_path = await crew.generate_ticket(question_data)
        print(f"Ticket created at: {ticket_path}")

        navigation_data = await crew.analyze_navigation(image_path="data/test_screenshot.png")
        print(f"Navigation analysis: {navigation_data}")

    asyncio.run(main())