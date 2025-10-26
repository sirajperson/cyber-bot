import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class SteghideToolInput(BaseModel):
    """Input schema for SteghideTool."""
    cover_file_path: str = Field(..., description="Path to the cover file (e.g., JPG, BMP, WAV, AU) suspected to contain hidden data, relative to '/app/data'.")
    passphrase: Optional[str] = Field(None, description="The passphrase required to extract the hidden data. If None or empty, attempts extraction without a passphrase.")
    output_file_path: Optional[str] = Field(None, description="Optional: Path to save the extracted data, relative to '/app/data'. If not provided, steghide might print to stdout or use the original embedded filename.")
    extract_only: bool = Field(True, description="Mode of operation. Currently only supports extraction ('extract'). Set to True.")

class SteghideTool(BaseTool):
    name: str = "Steghide Extractor"
    description: str = (
        "Attempts to extract hidden data embedded in media files (like JPG, BMP, WAV, AU) using the 'steghide' steganography tool. "
        "Requires the path to the cover file (relative to '/app/data'). Optionally takes a passphrase and an output file path. "
        "Currently only supports extraction."
    )
    args_schema: Type[BaseModel] = SteghideToolInput

    def _run(self, cover_file_path: str, passphrase: Optional[str] = None,
             output_file_path: Optional[str] = None, extract_only: bool = True) -> str:
        """
        Executes the 'steghide extract' command.
        """
        if not extract_only:
             return "Error: This tool currently only supports the 'extract' mode for steghide."

        # --- Security/Context Check ---
        base_dir = "/app/data"
        # Sanitize cover file path
        cover_relative = os.path.normpath(os.path.join('/', cover_file_path.lstrip('/'))).lstrip('/')
        target_cover_file = os.path.abspath(os.path.join(base_dir, cover_relative))

        if not target_cover_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {cover_file_path}")
            return f"Error: Invalid cover file path '{cover_file_path}'. Path must be within the data directory."
        if not os.path.isfile(target_cover_file):
             logger.error(f"Cover file not found for steghide: '{target_cover_file}'")
             return f"Error: Cover file not found at '{target_cover_file}'."

        # Sanitize output file path if provided
        target_out_file_abs = None
        out_relative = None
        if output_file_path:
            out_relative = os.path.normpath(os.path.join('/', output_file_path.lstrip('/'))).lstrip('/')
            target_out_file_abs = os.path.abspath(os.path.join(base_dir, out_relative))
            if not target_out_file_abs.startswith(base_dir):
                 logger.warning(f"Invalid output file path (potential traversal): {output_file_path}")
                 return f"Error: Invalid output file path '{output_file_path}'. Must be within data directory."
            # Ensure output directory exists
            try:
                os.makedirs(os.path.dirname(target_out_file_abs), exist_ok=True)
            except OSError as e:
                 logger.error(f"Could not create directory for steghide output '{target_out_file_abs}': {e}")
                 return f"Error: Could not create output directory for '{output_file_path}'."


        # --- Construct Command ---
        command = ["steghide", "extract", "-sf", target_cover_file, "-f"] # -f to force overwrite if output file exists

        if passphrase:
            command.extend(["-p", passphrase])
        # If output_file_path is given, steghide usually ignores the embedded filename and saves there.
        # If not given, steghide tries to use the embedded filename in the CWD (which we set to /app/data).
        if target_out_file_abs:
             command.extend(["-xf", target_out_file_abs])


        # Execute in the data directory so relative output works if -xf not used
        cwd = base_dir
        logger.info(f"Executing command (passphrase omitted): {' '.join(shlex.quote(c) for c in command)} in CWD: {cwd}")

        # --- Execute Command ---
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors='ignore',
                check=False,
                timeout=60,
                cwd=cwd # Set current working directory
            )

            # --- Process Output ---
            # Steghide typically prints status to stdout
            output = f"Steghide extraction attempt on '{cover_file_path}':\n"
            if result.stdout:
                output += f"--- stdout ---\n{result.stdout.strip()}\n"
            else:
                 output += "--- stdout ---\n(No standard output)\n"
            if result.stderr:
                output += f"--- stderr ---\n{result.stderr.strip()}\n"
            output += f"Exit Code: {result.returncode}\n"

            if result.returncode == 0 and "wrote extracted data to" in result.stdout:
                 extracted_file_mentioned = result.stdout.split("wrote extracted data to")[-1].strip().strip('"').strip("'")
                 # Check if the mentioned file (or the specified output file) actually exists
                 final_output_path = target_out_file_abs if target_out_file_abs else os.path.join(cwd, extracted_file_mentioned)
                 final_output_relative = out_relative if out_relative else extracted_file_mentioned

                 if os.path.exists(final_output_path):
                     output += f"\nSuccess: Extracted data saved to '/app/data/{final_output_relative}'. Use other tools (like 'file', 'cat') to inspect it."
                     logger.info(f"Steghide extraction successful for {target_cover_file}")
                 else:
                     # This might happen if -xf was used but steghide failed writing despite exit 0
                     output += f"\nWarning: Steghide reported success but the output file ('/app/data/{final_output_relative}') was not found. Check stdout/stderr."
                     logger.warning(f"Steghide reported success for {target_cover_file} but output file missing.")

            elif "could not extract" in result.stdout or "passphrase is incorrect" in result.stdout:
                logger.warning(f"Steghide failed extraction (e.g., wrong passphrase) for {target_cover_file}.")
                output += "\nResult: Extraction failed (likely incorrect passphrase or no data found)."
            elif result.returncode != 0:
                 logger.error(f"Steghide command failed for {target_cover_file}. Exit: {result.returncode}. Output: {result.stdout.strip()} Stderr: {result.stderr.strip()}")
                 output += "\nError: Steghide command failed. Check stdout/stderr above for details."
            else:
                 # Exit 0 but no success message? Could mean no data found.
                  logger.info(f"Steghide completed for {target_cover_file} but didn't report writing data.")
                  output += "\nResult: Steghide completed, but may not have found any data to extract."


            max_len = 2000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Steghide command timed out for file '{cover_file_path}'.")
            return f"Error: Steghide command timed out on '{cover_file_path}'."
        except FileNotFoundError:
            logger.error("'steghide' command not found.")
            return "Error: 'steghide' command not found."
        except Exception as e:
            logger.error(f"Error running steghide on '{cover_file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running steghide: {e}"

# Example usage (requires steghide and dummy files)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = SteghideTool()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)

    # Relative paths for agent input
    cover_rel = "cover_image.jpg"
    secret_rel = "secret.txt"
    output_rel = "extracted_secret.txt"
    # Absolute paths for creation/cleanup
    cover_abs = os.path.join(data_dir_abs, cover_rel)
    secret_abs = os.path.join(data_dir_abs, secret_rel)
    output_abs = os.path.join(data_dir_abs, output_rel)
    passphrase = "testpass"

    embed_success = False
    try:
        # Create dummy cover file (needs a format steghide supports, e.g. JPG)
        # Creating a valid JPG programmatically is tricky, use placeholder text file for basic test run
        # For a real test, place a small JPG file named cover_image.jpg in the data directory
        if not os.path.exists(cover_abs):
             print(f"WARNING: Dummy cover file '{cover_abs}' not found. Creating placeholder text file. Steghide will likely fail, but tests command structure.")
             with open(cover_abs, "w") as f: f.write("This is a placeholder cover file.\n")

        # Create dummy secret file
        with open(secret_abs, "w") as f: f.write("This is the hidden message.\n")
        print(f"Created dummy secret file: {secret_abs}")

        # Embed using steghide on host (requires steghide) - This will likely fail if cover_abs is text
        # But we try anyway to test command path finding
        embed_cmd = ["steghide", "embed", "-cf", cover_abs, "-ef", secret_abs, "-p", passphrase, "-f"]
        print(f"Attempting to embed using (passphrase omitted): {' '.join(shlex.quote(c) for c in embed_cmd if c != passphrase)}")
        try:
             embed_result = subprocess.run(embed_cmd, check=True, capture_output=True, text=True, timeout=10)
             print("Embedding seemingly successful (might have failed silently on text file).")
             embed_success = True # Set flag even if it might fail on text cover
        except FileNotFoundError:
             print("WARNING: 'steghide' command not found on host. Cannot perform embedding test.")
        except subprocess.CalledProcessError as e:
             print(f"WARNING: Embedding failed (as expected for text cover?): {e.stderr}")
             embed_success = False # Embedding definitely failed
        except subprocess.TimeoutExpired:
              print("WARNING: Embedding command timed out.")


        print("\n--- Test 1: Extract with correct passphrase ---")
        # Agent provides relative paths
        result1 = tool.run(cover_file_path=cover_rel, passphrase=passphrase, output_file_path=output_rel)
        print(result1)
        # Check if output file was created (if embed worked)

        print("\n--- Test 2: Extract with incorrect passphrase ---")
        result2 = tool.run(cover_file_path=cover_rel, passphrase="wrongpass", output_file_path=output_rel)
        print(result2)

        print("\n--- Test 3: Extract without passphrase ---")
        result3 = tool.run(cover_file_path=cover_rel, output_file_path=output_rel)
        print(result3)

        print("\n--- Test 4: Non-existent cover file ---")
        result4 = tool.run(cover_file_path="nosuchcover.jpg")
        print(result4)

    except Exception as e:
         print(f"Error during test setup or execution: {e}")
    finally:
        # Clean up
        files_to_remove = [cover_abs, secret_abs, output_abs]
        for f in files_to_remove:
             if f and os.path.exists(f): os.remove(f)
        print(f"\nCleaned up test files.")
