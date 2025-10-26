import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class SedToolInput(BaseModel):
    """Input schema for SedTool."""
    sed_script: str = Field(..., description="The sed script or command to execute (e.g., 's/INFO/Information/g', '/ERROR/d'). Should be properly quoted if necessary for the shell.")
    file_path: str = Field(..., description="The path to the input file to process, relative to the '/app/data' directory.")
    in_place: bool = Field(False, description="Modify the file in-place ('-i' flag). ⚠️ Use with extreme caution. Defaults to False, printing changes to stdout.")

class SedTool(BaseTool):
    name: str = "Sed Stream Editor"
    description: str = (
        "Performs text transformations on an input file using the 'sed' stream editor. "
        "Useful for substitutions, deletions, or printing specific lines based on patterns. "
        "Provide the sed script/command and the input file path (relative to '/app/data'). "
        "By default, it prints the transformed output; use 'in_place=True' cautiously to modify the file directly."
    )
    args_schema: Type[BaseModel] = SedToolInput

    def _run(self, sed_script: str, file_path: str, in_place: bool = False) -> str:
        """
        Executes the 'sed' command.
        """
        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', file_path.lstrip('/'))).lstrip('/')
        target_file = os.path.abspath(os.path.join(base_dir, relative_path))

        if not target_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {file_path}")
            return f"Error: Invalid file path '{file_path}'. Path must be within the data directory."
        if not os.path.isfile(target_file):
            logger.error(f"Input file not found for sed: '{target_file}'")
            return f"Error: File not found at '{target_file}'."
        if in_place:
             logger.warning(f"Executing sed with in-place modification enabled on file: {target_file}")


        # --- Construct Command ---
        command = ["sed"]
        if in_place:
            command.append("-i") # Modify in-place

        # Add the script. Pass it as a single argument.
        command.append(sed_script)

        # Add the target file
        command.append(target_file)

        logger.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")

        # --- Execute Command ---
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors='ignore',
                check=False,
                timeout=60
            )

            # --- Process Output ---
            # If -i is used, stdout is usually empty. If not, stdout contains the transformed text.
            output = f"Sed execution result for '{file_path}' with script '{sed_script}' (in_place={in_place}):\n"
            if result.stdout:
                output += f"--- Transformed Output (stdout) ---\n```\n{result.stdout.strip()}\n```\n"
            elif not in_place:
                 output += "--- Transformed Output (stdout) ---\n(No standard output generated)\n"
            else: # In-place modification
                 output += "--- Transformed Output (stdout) ---\n(In-place modification requested, no stdout expected on success)\n"

            if result.stderr:
                output += f"--- stderr ---\n{result.stderr.strip()}\n"
            output += f"Exit Code: {result.returncode}\n"

            if result.returncode != 0:
                logger.error(f"Sed command failed for {target_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                output += "\nError: Sed command failed. Check script syntax or file permissions."
            else:
                 logger.info(f"Sed command successful for {target_file}")
                 if in_place:
                      output += f"\nSuccess: File '{file_path}' modified in-place."
                 else:
                      output += f"\nSuccess: Transformed output printed above."


            max_len = 5000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Sed command timed out for file '{file_path}'.")
            return f"Error: Sed command timed out on '{file_path}'."
        except FileNotFoundError:
            logger.error("'sed' command not found.")
            return "Error: 'sed' command not found."
        except Exception as e:
            logger.error(f"Error running sed on '{file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running sed: {e}"

# Example usage (requires sed and a test file)
if __name__ == "__main__":
    import re # For main block
    logging.basicConfig(level=logging.INFO)
    tool = SedTool()
    # Create dummy data file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)
    test_file_rel = "test_sed.log"
    test_file_abs = os.path.join(data_dir_abs, test_file_rel)
    original_content = "INFO: Process started PID=123\nWARN: Disk low\nERROR: Failed login IP=1.2.3.4\nINFO: Process ended PID=123\n"
    try:
        with open(test_file_abs, "w") as f: f.write(original_content)
        print(f"Created dummy log file: {test_file_abs}")

        print("\n--- Test 1: Substitute 'INFO' with 'Information' (Print Only) ---")
        result1 = tool.run(file_path=test_file_rel, sed_script='s/INFO/Information/g')
        print(result1)

        print("\n--- Test 2: Delete lines containing 'WARN' (Print Only) ---")
        result2 = tool.run(file_path=test_file_rel, sed_script='/WARN/d')
        print(result2)

        # --- In-place test ---
        print("\n--- Test 3: Substitute 'PID=' with 'ProcessID=' (In-Place) ---")
        # Rerun to ensure original content before modifying
        with open(test_file_abs, "w") as f: f.write(original_content)
        result3 = tool.run(file_path=test_file_rel, sed_script='s/PID=/ProcessID=/g', in_place=True)
        print(result3)
        print("--- Verifying In-Place Change ---")
        if os.path.exists(test_file_abs):
             with open(test_file_abs, "r") as f: print(f.read())
        else: print("File missing after in-place edit?")


        print("\n--- Test 4: Invalid sed script ---")
        result4 = tool.run(file_path=test_file_rel, sed_script='s/Invalid') # Malformed substitute
        print(result4)

    finally:
        if os.path.exists(test_file_abs): os.remove(test_file_abs)
        print("\nCleaned up test file.")
