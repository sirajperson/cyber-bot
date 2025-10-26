import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class ForemostToolInput(BaseModel):
    """Input schema for ForemostTool."""
    image_file_path: str = Field(..., description="The path to the disk image or file to carve data from, relative to the '/app/data' directory.")
    output_directory: str = Field("foremost_output", description="Name of the directory to store carved files, relative to '/app/data'. Defaults to 'foremost_output'.")
    config_file: Optional[str] = Field(None, description="Path to a custom foremost configuration file (relative to '/app/data'), if needed.")
    file_types: Optional[str] = Field(None, description="Comma-separated list of specific file types to carve (e.g., 'jpg,pdf,zip'). Defaults to all types in foremost config.")

class ForemostTool(BaseTool):
    name: str = "Foremost File Carver"
    description: str = (
        "Carves and recovers files from disk images or data files based on file headers, footers, and data structures (data carving). "
        "Useful for recovering deleted files or extracting files from raw data streams when file system metadata is missing. "
        "Operates on files within '/app/data' and saves output to a subdirectory within '/app/data'."
    )
    args_schema: Type[BaseModel] = ForemostToolInput

    def _run(self, image_file_path: str, output_directory: str = "foremost_output",
             config_file: Optional[str] = None, file_types: Optional[str] = None) -> str:
        """
        Executes the 'foremost' command.
        """
        # --- Security/Context Check ---
        base_dir = "/app/data"
        # Sanitize image path
        in_relative = os.path.normpath(os.path.join('/', image_file_path.lstrip('/'))).lstrip('/')
        target_in_file = os.path.abspath(os.path.join(base_dir, in_relative))
        # Sanitize and create output directory path
        # Ensure output dir name is safe (e.g., no '..') and create it
        safe_out_dir_name = os.path.basename(output_directory or "foremost_output") # Use basename to prevent traversal in name
        target_out_dir = os.path.abspath(os.path.join(base_dir, safe_out_dir_name))

        if not target_in_file.startswith(base_dir) or not target_out_dir.startswith(base_dir):
            logger.warning(f"Attempted path traversal: in='{image_file_path}', out='{output_directory}'")
            return f"Error: Invalid paths. Input image and output directory must resolve within the data directory."
        if not os.path.isfile(target_in_file):
             logger.error(f"Input file not found for foremost: '{target_in_file}'")
             return f"Error: Input file not found at '{target_in_file}'."
        # Create output dir (relative to base_dir)
        try:
            # Create within base_dir to be safe
            os.makedirs(target_out_dir, exist_ok=True)
        except OSError as e:
             logger.error(f"Could not create foremost output directory '{target_out_dir}': {e}")
             return f"Error: Could not create output directory '{safe_out_dir_name}'. Check permissions."

        # Sanitize config file path if provided
        target_config_file = None
        if config_file:
            conf_relative = os.path.normpath(os.path.join('/', config_file.lstrip('/'))).lstrip('/')
            target_config_file = os.path.abspath(os.path.join(base_dir, conf_relative))
            if not target_config_file.startswith(base_dir):
                 logger.warning(f"Invalid config file path (potential traversal): {config_file}")
                 return f"Error: Invalid config file path '{config_file}'. Must be within data directory."
            if not os.path.isfile(target_config_file):
                 logger.error(f"Custom foremost config file not found: '{target_config_file}'")
                 return f"Error: Custom config file not found at '{target_config_file}'."


        # --- Construct Command ---
        command = ["foremost", "-v"] # Verbose output is useful
        if config_file and target_config_file:
            command.extend(["-c", target_config_file])
        if file_types:
            # Basic validation/sanitization for file types (avoid shell injection)
            safe_types = ','.join(t.strip() for t in file_types.split(',') if t.strip().isalnum())
            if safe_types:
                 command.extend(["-t", safe_types])
            else:
                 logger.warning(f"Invalid characters in file_types argument: '{file_types}'. Ignoring.")

        # Specify output directory and input file
        command.extend(["-o", target_out_dir])
        command.extend(["-i", target_in_file])

        logger.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")

        # --- Execute Command ---
        try:
            # Foremost can take time on large images
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors='ignore',
                check=False,
                timeout=600 # 10 minutes timeout
            )

            # --- Process Output ---
            # Foremost output (summary) usually goes to stderr
            output = f"Foremost file carving for '{image_file_path}' into '{safe_out_dir_name}':\n"
            if result.stderr:
                output += f"--- Process Log (stderr) ---\n{result.stderr.strip()}\n"
            else:
                 output += "--- Process Log (stderr) ---\n(No standard error output)\n"
            if result.stdout: # stdout might contain errors or unexpected output
                 output += f"--- stdout ---\n{result.stdout.strip()}\n"

            output += f"Exit Code: {result.returncode}\n"

            if result.returncode == 0:
                 # Check if output dir actually contains files (simple check)
                 try:
                      carved_files = [f for f in os.listdir(target_out_dir) if f != 'audit.txt']
                      if carved_files:
                           num_files = len(carved_files)
                           output += f"\nSuccess: Foremost completed. Found {num_files} potential file(s)/directories in '/app/data/{safe_out_dir_name}'. Check the audit.txt file there for details."
                           logger.info(f"Foremost completed successfully for {target_in_file}, found files.")
                      else:
                           output += f"\nSuccess: Foremost completed, but no files appear to have been carved into '/app/data/{safe_out_dir_name}'. Check the audit.txt file there."
                           logger.info(f"Foremost completed successfully for {target_in_file}, but no files carved.")
                 except Exception as list_err:
                      output += f"\nSuccess: Foremost completed. Check the output directory '/app/data/{safe_out_dir_name}' and audit.txt. (Error listing files: {list_err})"
                      logger.warning(f"Foremost completed for {target_in_file}, but couldn't list output dir contents: {list_err}")

            else:
                 logger.error(f"Foremost failed for {target_in_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                 output += "\nError: Foremost failed. Check stderr output above for details."


            max_len = 4000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Foremost command timed out for file '{image_file_path}'.")
            return f"Error: Foremost command timed out on '{image_file_path}'."
        except FileNotFoundError:
            logger.error("'foremost' command not found.")
            return "Error: 'foremost' command not found."
        except Exception as e:
            logger.error(f"Error running foremost on '{image_file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running foremost: {e}"

# Example usage (requires foremost and a test file)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = ForemostTool()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)

    # Relative path for agent input
    test_image_rel = "test_foremost_image.dd"
    # Absolute path for creation
    test_image_abs = os.path.join(data_dir_abs, test_image_rel)
    # Relative path for output dir name
    output_dir_rel = "test_foremost_output"
    output_dir_abs = os.path.join(data_dir_abs, output_dir_rel)


    try:
        # Create a dummy image file with an embedded known header (e.g., JPEG)
        with open(test_image_abs, "wb") as f:
            f.write(os.urandom(1024)) # Some leading garbage
            f.write(b"\xFF\xD8\xFF\xE0") # JPEG SOI + APP0 marker
            f.write(b"JFIF\x00")
            f.write(os.urandom(2048)) # Some data
            f.write(b"This looks like text")
            f.write(os.urandom(1024))
            f.write(b"\xFF\xD9") # JPEG EOI marker
            f.write(os.urandom(512)) # Trailing garbage
        print(f"Created dummy image file: {test_image_abs}")

        print("\n--- Test 1: Run foremost carving ---")
        # Agent provides relative paths
        result1 = tool.run(image_file_path=test_image_rel, output_directory=output_dir_rel, file_types="jpg")
        print(result1)
        # Check if output dir and jpg subdir were created in local data/

        print("\n--- Test 2: Non-existent input file ---")
        result2 = tool.run(image_file_path="nosuchimage.dd")
        print(result2)

    except Exception as e:
         print(f"Error during test setup or execution: {e}")
    finally:
        # Clean up
        if os.path.exists(test_image_abs): os.remove(test_image_abs)
        if os.path.isdir(output_dir_abs):
             import shutil
             shutil.rmtree(output_dir_abs)
             print(f"Cleaned up output directory: {output_dir_abs}")
        print(f"\nCleaned up test files.")
