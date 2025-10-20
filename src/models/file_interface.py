from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os

class FileInterface(ABC):
    """
    Interface defining the contract for file handling operations in the Cyber Bot project.
    This interface provides methods for downloading files, saving markdown content, listing
    downloaded files, and managing file metadata, ensuring consistent file operations
    across the application (e.g., for module downloads and ticket generation).
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass