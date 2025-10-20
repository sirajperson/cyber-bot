import os
import requests
from datetime import datetime
import logging
from typing import List, Dict, Any
from src.models.file_interface import FileInterface

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileHandler(FileInterface):
    """
    Concrete implementation of FileInterface for handling file operations in the Cyber Bot project.
    This class manages downloading module files, saving markdown content, listing downloads,
    retrieving metadata, and deleting files, serving as a shared utility across the application.
    """

    def download_file(self, url: str, destination: str) -> bool:
        """
        Download a file from the given URL to the specified destination path.

        Args:
            url (str): The URL of the file to download (e.g., PDF or ZIP from a module).
            destination (str): The local file path where the file will be saved.

        Returns:
            bool: True if the download is successful, False otherwise.

        Raises:
            ValueError: If the URL or destination is invalid.
            IOError: If the file cannot be written to the destination.
            requests.RequestException: If the network request fails.
        """
        try:
            if not url or not destination:
                raise ValueError("URL and destination must be provided")
            os.makedirs(os.path.dirname(destination) or '.', exist_ok=True)
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Downloaded {url} to {destination}")
            return True
        except requests.RequestException as e:
            logger.error(f"Download failed for {url}: {str(e)}")
            return False
        except IOError as e:
            logger.error(f"IO error writing to {destination}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {str(e)}")
            return False

    def save_markdown(self, content: str, path: str) -> bool:
        """
        Save the provided markdown content to the specified file path.

        Args:
            content (str): The markdown text to save.
            path (str): The local file path where the markdown will be saved.

        Returns:
            bool: True if the save is successful, False otherwise.

        Raises:
            ValueError: If the content or path is invalid.
            IOError: If the file cannot be written.
        """
        try:
            if not content or not path:
                raise ValueError("Content and path must be provided")
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Saved markdown to {path}")
            return True
        except IOError as e:
            logger.error(f"IO error writing to {path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving markdown to {path}: {str(e)}")
            return False

    def list_downloads(self, directory: str) -> List[str]:
        """
        List all downloaded files in the specified directory.

        Args:
            directory (str): The directory path to scan for downloaded files.

        Returns:
            List[str]: A list of absolute file paths to downloaded files.

        Raises:
            FileNotFoundError: If the directory does not exist.
            OSError: If the directory cannot be accessed.
        """
        try:
            if not os.path.isdir(directory):
                raise FileNotFoundError(f"Directory {directory} not found")
            return [os.path.join(directory, f) for f in os.listdir(directory)
                    if os.path.isfile(os.path.join(directory, f)) and not f.startswith('.')]
        except FileNotFoundError as e:
            logger.error(f"Directory not found: {str(e)}")
            return []
        except OSError as e:
            logger.error(f"OS error accessing {directory}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing downloads in {directory}: {str(e)}")
            return []

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific file.

        Args:
            file_path (str): The path to the file to inspect.

        Returns:
            Dict[str, Any]: Metadata including 'size' (in bytes), 'mtime' (last modified time),
                           and 'name' (file name).

        Raises:
            FileNotFoundError: If the file does not exist.
            OSError: If the file metadata cannot be accessed.
        """
        try:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File {file_path} not found")
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'mtime': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'name': os.path.basename(file_path)
            }
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            return {}
        except OSError as e:
            logger.error(f"OS error accessing metadata for {file_path}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting metadata for {file_path}: {str(e)}")
            return {}

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file at the specified path.

        Args:
            file_path (str): The path to the file to delete.

        Returns:
            bool: True if the deletion is successful, False otherwise.

        Raises:
            OSError: If the file cannot be deleted.
            PermissionError: If there is insufficient permission to delete the file.
        """
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file {file_path}")
                return True
            logger.warning(f"File not found for deletion: {file_path}")
            return False
        except PermissionError as e:
            logger.error(f"Permission denied deleting {file_path}: {str(e)}")
            return False
        except OSError as e:
            logger.error(f"OS error deleting {file_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting {file_path}: {str(e)}")
            return False

if __name__ == "__main__":
    # Example usage for testing
    handler = FileHandler()
    # Test download
    if handler.download_file("https://example.com/sample.pdf", "data/sample.pdf"):
        print("Download successful")
    # Test save markdown
    if handler.save_markdown("# Test", "data/test.md"):
        print("Markdown saved")
    # Test list downloads
    downloads = handler.list_downloads("data")
    print(f"Downloads: {downloads}")
    # Test metadata
    metadata = handler.get_file_metadata("data/test.md")
    print(f"Metadata: {metadata}")
    # Test delete
    if handler.delete_file("data/test.md"):
        print("File deleted")