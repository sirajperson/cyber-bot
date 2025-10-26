import os
import logging
from typing import Type, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class AutopsyToolInput(BaseModel):
    """Input schema for AutopsyTool."""
    image_file_path: str = Field(..., description="The path to the disk image file (e.g., .dd, .e01, .raw) to analyze, relative to the '/app/data' directory.")
    case_name: str = Field("CyberBot_Case", description="A name for the Autopsy case.")

class AutopsyTool(BaseTool):
    name: str = "Autopsy Instructions (Disk Forensics)"
    description: str = (
        "Provides instructions on how to use Autopsy, a GUI-based digital forensics platform, "
        "to analyze disk images (.dd, .e01, raw, etc.). Use this when a disk image needs investigation "
        "for file recovery, timeline analysis, keyword searching, etc. "
        "Input the disk image path relative to '/app/data'."
    )
    args_schema: Type[BaseModel] = AutopsyToolInput

    def _run(self, image_file_path: str, case_name: str = "CyberBot_Case") -> str:
        """
        Returns instructions for using Autopsy.
        """
        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', image_file_path.lstrip('/'))).lstrip('/')
        target_file_abs = os.path.abspath(os.path.join(base_dir, relative_path))
        target_file_container_path = f"/app/data/{relative_path}" # Path as seen inside container

        if not target_file_abs.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {image_file_path}")
            return f"Error: Invalid file path '{image_file_path}'. Path must be within the data directory."
        # Note: No existence check needed.

        logger.info(f"Generating Autopsy instructions for: {target_file_container_path}")

        # --- Generate Instructions ---
        instructions = f"""
        **Instructions for Analyzing Disk Image:** '{target_file_container_path}' **using Autopsy**

        **Autopsy** is a graphical interface for The Sleuth Kit and other digital forensics tools. (Requires separate installation, potentially outside the standard container). 

        **General Steps:**
        1.  **Launch Autopsy:** Start the Autopsy application.
        2.  **Create/Open Case:** Create a new case (e.g., named '{case_name}') or open an existing one. Provide necessary case details.
        3.  **Add Data Source:**
            * Select 'Disk Image or VM File' as the data source type.
            * Browse to and select the image file: `{target_file_container_path}`.
            * Configure Ingest Modules: Select relevant modules to run during analysis (e.g., Recent Activity, Hash Lookup, Keyword Search, File Type Identification, EXIF Parser, Extension Mismatch Detector). Keyword lists can be added here.
            * Start the ingest process. This may take a significant amount of time depending on image size and selected modules.
        4.  **Analyze Data:** Once ingest is complete, explore the data using the tree view on the left:
            * **File Views:** Browse by file type, deleted files, file size, etc.
            * **Data Artifacts:** Examine extracted information like web history, registry entries (if Windows), EXIF data, emails.
            * **Timeline:** Analyze file system activity over time.
            * **Keyword Search:** Search for specific terms across the entire image.
        5.  **Examine Files:** View files in different formats (Hex, Text, Strings, Media). Extract/export relevant files.
        6.  **Look for Flags:** Search specifically for flag formats (e.g., `FLAG{{...}}`, `CTF{{...}}`) or keywords mentioned in the challenge description.

        **Focus Areas for CTFs:**
        * Deleted files or file fragments.
        * User directories, downloads, documents, browser history/cache.
        * Interesting file names or extensions.
        * Files containing keywords from the challenge prompt.
        * Unallocated space (may require specific ingest modules or carving tools like Foremost/Scalpel, which Autopsy can integrate).

        **Note:** Direct execution/control of Autopsy (a GUI tool) is not available through this interface. Include these steps in your analysis plan. Ensure Autopsy is installed and the image file path is accessible to it.
        """

        return instructions.strip()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = AutopsyTool()
    print("--- Test 1: Generate instructions ---")
    result1 = tool.run(image_file_path="evidence.dd")
    print(result1)
