from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class AgentInterface(ABC):
    """
    Interface defining the contract for agent operations in the Cyber Bot project,
    integrating with CrewAI for module processing, ticket generation, and navigation support.
    This interface ensures consistent behavior for agent-based tasks such as module content
    extraction, question analysis, and navigation guidance using vision models.
    """

    @abstractmethod
    def process_module(self, module_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process module data to extract and format content (e.g., objectives, questions).

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
        """
        pass

    @abstractmethod
    def generate_ticket(self, question_data: Dict[str, Any]) -> str:
        """
        Generate a ticket file path and content for a specific question.

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
        pass

    @abstractmethod
    def analyze_navigation(self, image_path: Optional[str] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
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
        pass