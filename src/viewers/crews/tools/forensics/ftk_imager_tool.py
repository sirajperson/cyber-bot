import os
import logging
from typing import Type, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class FtkImagerToolInput(BaseModel):
    """Input schema for FtkImagerTool."""
    image_file_path: str = Field(..., description="The path to the disk image file (e.g., .dd, .e01, .raw) to analyze, relative to the '/app/data' directory.")

class FtkImagerTool(BaseTool):
    name: str = "FTK Imager Instructions (Disk Forensics)"
    description: str = (
        "Provides instructions on how to use AccessData FTK Imager, a free GUI-based tool (Windows), "
        "to preview, mount, or analyze disk images (.dd, .e01, raw, VMDK, etc.). Use this for basic exploration "
        "of disk image contents, file recovery previews, or mounting images. "
        "Input the disk image path relative to '/app/data'."
    )
    args_schema: Type[BaseModel] = FtkImagerToolInput

    def _run(self, image_file_path: str) -> str:
        """
        Returns instructions for using FTK Imager.
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

        logger.info(f"Generating FTK Imager instructions for: {target_file_container_path}")

        # --- Generate Instructions ---
        instructions = f"""
        **Instructions for Analyzing Disk Image:** '{target_file_container_path}' **using FTK Imager**

        **FTK Imager** is a free data preview and imaging tool from AccessData (Windows only). 

        **Common Uses & Steps:**
        1.  **Launch FTK Imager:** Start the application on a Windows system.
        2.  **Add Evidence Item:**
            * Go to File > Add Evidence Item...
            * Select 'Image File' as the source type.
            * Browse to and select the image file: `{target_file_container_path}` (Ensure the file is accessible from the Windows machine running FTK Imager).
            * Click Finish.
        3.  **Explore Contents:** The image will appear in the 'Evidence Tree' pane (usually top-left). Expand the partitions and file systems to browse the directory structure and files, similar to Windows Explorer.
        4.  **Preview Files:** Select files in the 'File List' pane (usually top-right) to preview their contents in the viewer pane below (supports various formats like text, hex, images).
        5.  **View Properties/Metadata:** Right-click on files/folders to view properties, including timestamps and basic metadata.
        6.  **Export/Recover Files:** Select files or folders, right-click, and choose 'Export Files...' to save them to your host machine. This can often recover deleted files visible in the tool.
        7.  **Mount Image (Optional):** FTK Imager can also mount images as read-only drives in Windows, allowing other tools to access the contents. (File > Image Mounting...).

        **Focus Areas for CTFs:**
        * Browsing user directories, common locations (Desktop, Documents, Downloads).
        * Looking at deleted files (often marked differently).
        * Previewing images, documents, or text files for flags or hints.
        * Checking metadata of specific files.

        **Note:** Direct execution/control of FTK Imager (a Windows GUI tool) is not available. This tool requires a Windows environment. Use these instructions to guide manual analysis or include them in a plan. For more in-depth analysis (timeline, keyword search), consider Autopsy (cross-platform, GUI).
        """

        return instructions.strip()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = FtkImagerTool()
    print("--- Test 1: Generate instructions ---")
    result1 = tool.run(image_file_path="disk_image.e01")
    print(result1)
