import subprocess
import os
import logging
import shlex
from typing import Type, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class ExifToolWrapperInput(BaseModel):
    """Input schema for ExifToolWrapper."""
    file_path: str = Field(..., description="The path to the file (image, PDF, document, etc.) to read metadata from, relative to the '/app/data' directory.")
    extra_args: Optional[str] = Field("", description="Any additional exiftool command line arguments (e.g., '-l' for long output, '-G' for group names).")

class ExifToolWrapper(BaseTool):
    name: str = "ExifTool Metadata Reader"
    description: str = (
        "Reads metadata (EXIF, IPTC, XMP, GPS, etc.) from various file types like images, PDFs, and documents "
        "using the 'exiftool' command. Operates on files within the '/app/data' directory. "
        "Provide the file path relative to '/app/data'."
    )
    args_schema: Type[BaseModel] = ExifToolWrapperInput

    def _run(self, file_path: str, extra_args: Optional[str] = "") -> str:
        """
        Executes the 'exiftool' command on the specified file.
        """
        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', file_path.lstrip('/'))).lstrip('/')
        target_file = os.path.abspath(os.path.join(base_dir, relative_path))

        if not target_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {file_path}")
            return f"Error: Invalid file path '{file_path}'. Path must be within the data directory."
        if not os.path.isfile(target_file):
             logger.error(f"File not found for exiftool: '{target_file}'")
             return f"Error: File not found at '{target_file}'."

        # --- Construct Command ---
        command = ["exiftool"]
        if extra_args:
            command.extend(shlex.split(extra_args)) # Use shlex to handle quoted args
        command.append(target_file)
        logger.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")

        # --- Execute Command ---
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors='ignore', # Ignore potential decoding errors in metadata
                check=False,
                timeout=30
            )

            # --- Process Output ---
            output = f"Exiftool metadata for '{file_path}':\n"
            if result.stdout:
                output += f"--- stdout ---\n```\n{result.stdout.strip()}\n```\n"
            else:
                 output += "--- stdout ---\n(No metadata found or command failed)\n"
            if result.stderr:
                output += f"--- stderr ---\n{result.stderr.strip()}\n"
            output += f"Exit Code: {result.returncode}\n"

            if result.returncode != 0:
                 logger.error(f"Exiftool failed for {target_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")

            max_len = 6000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Exiftool command timed out for '{file_path}'.")
            return f"Error: Exiftool command timed out on '{file_path}'."
        except FileNotFoundError:
            logger.error("'exiftool' command not found.")
            return "Error: 'exiftool' command not found."
        except Exception as e:
            logger.error(f"Error running exiftool on '{file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running exiftool: {e}"

# Example usage (requires exiftool and a test file)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = ExifToolWrapper()
    # Create a dummy file in ./data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)
    test_file_rel = "test_exif.txt"
    test_file_abs = os.path.join(data_dir_abs, test_file_rel)
    try:
        with open(test_file_abs, "w") as f: f.write("Simple text file\n")
        print(f"Created dummy file: {test_file_abs}")

        print("\n--- Test 1: Run exiftool on text file ---")
        result1 = tool.run(file_path=test_file_rel)
        print(result1) # Should show basic file metadata

        # Add image test if you have Pillow installed for test setup
        # from PIL import Image
        # test_img_rel = "test_exif.jpg"
        # test_img_abs = os.path.join(data_dir_abs, test_img_rel)
        # try:
        #     img = Image.new('RGB', (60, 30), color = 'red')
        #     # Add some exif data if possible with Pillow or external lib
        #     img.save(test_img_abs)
        #     print(f"Created dummy image: {test_img_abs}")
        #     print("\n--- Test 2: Run exiftool on image file ---")
        #     result2 = tool.run(file_path=test_img_rel)
        #     print(result2)
        # except ImportError:
        #      print("\n--- Skipping image test: Pillow not installed ---")
        # finally:
        #      if os.path.exists(test_img_abs): os.remove(test_img_abs)


    finally:
        if os.path.exists(test_file_abs): os.remove(test_file_abs)
        print("\nCleaned up dummy files.")
