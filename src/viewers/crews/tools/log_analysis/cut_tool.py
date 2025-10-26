import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class CutToolInput(BaseModel):
    """Input schema for CutTool."""
    file_path: str = Field(..., description="The path to the input file to process, relative to the '/app/data' directory.")
    delimiter: Optional[str] = Field(None, description="Delimiter character to use for splitting fields ('-d' option). E.g., ',', ':', '\\t'. If None, uses TAB by default.")
    fields: str = Field(..., description="Specifies fields/columns to select ('-f' option). E.g., '1', '1,3', '2-4'.")
    characters: Optional[str] = Field(None, description="Specifies character positions to select ('-c' option). E.g., '1-10', '5'. Use either fields or characters.")
    complement: bool = Field(False, description="Select all fields/characters *except* those specified ('--complement').")

class CutTool(BaseTool):
    name: str = "Cut Text Selector"
    description: str = (
        "Extracts sections (fields/columns or character positions) from each line of a file using the 'cut' command. "
        "Useful for processing delimited data (like CSV or colon-separated files). "
        "Provide the input file path (relative to '/app/data'), and specify either 'fields' (with an optional 'delimiter') or 'characters'."
    )
    args_schema: Type[BaseModel] = CutToolInput

    def _run(self, file_path: str, fields: str = None, delimiter: Optional[str] = None,
             characters: Optional[str] = None, complement: bool = False) -> str:
        """
        Executes the 'cut' command.
        """
        # --- Validate Inputs ---
        if not fields and not characters:
            return "Error: You must specify either 'fields' or 'characters' to cut."
        if fields and characters:
             return "Error: Specify either 'fields' or 'characters', not both."

        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', file_path.lstrip('/'))).lstrip('/')
        target_file = os.path.abspath(os.path.join(base_dir, relative_path))

        if not target_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {file_path}")
            return f"Error: Invalid file path '{file_path}'. Path must be within the data directory."
        if not os.path.isfile(target_file):
            logger.error(f"Input file not found for cut: '{target_file}'")
            return f"Error: File not found at '{target_file}'."

        # --- Construct Command ---
        command = ["cut"]

        if delimiter:
            command.extend(["-d", delimiter])
        if fields:
            # Basic validation: ensure fields look like numbers, commas, hyphens
            if not re.match(r'^[0-9,-]+$', fields):
                 return f"Error: Invalid format for 'fields': '{fields}'. Use numbers, commas, hyphens (e.g., '1,3-5')."
            command.extend(["-f", fields])
        elif characters:
             if not re.match(r'^[0-9,-]+$', characters):
                 return f"Error: Invalid format for 'characters': '{characters}'. Use numbers, commas, hyphens (e.g., '1-10,15')."
             command.extend(["-c", characters])

        if complement:
            command.append("--complement")

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
            output = f"Cut execution result for '{file_path}':\n"
            if result.stdout:
                output += f"--- stdout ---\n```\n{result.stdout.strip()}\n```\n"
            else:
                output += "--- stdout ---\n(No standard output generated)\n"
            if result.stderr:
                output += f"--- stderr ---\n{result.stderr.strip()}\n"
            output += f"Exit Code: {result.returncode}\n"

            if result.returncode != 0:
                logger.error(f"Cut command failed for {target_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                output += "\nError: Cut command failed. Check parameters and file format."

            max_len = 5000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Cut command timed out for file '{file_path}'.")
            return f"Error: Cut command timed out on '{file_path}'."
        except FileNotFoundError:
            logger.error("'cut' command not found.")
            return "Error: 'cut' command not found."
        except Exception as e:
            logger.error(f"Error running cut on '{file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running cut: {e}"

# Example usage (requires cut and a test file)
if __name__ == "__main__":
    import re # For main block
    logging.basicConfig(level=logging.INFO)
    tool = CutTool()
    # Create dummy data file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)
    test_file_rel = "test_cut.csv"
    test_file_abs = os.path.join(data_dir_abs, test_file_rel)
    try:
        with open(test_file_abs, "w") as f:
            f.write("ID,User,Action,Timestamp\n")
            f.write("1,admin,login,2025-10-26T12:00:00Z\n")
            f.write("2,guest,view,2025-10-26T12:05:00Z\n")
            f.write("3,admin,logout,2025-10-26T12:10:00Z\n")
        print(f"Created dummy CSV file: {test_file_abs}")

        print("\n--- Test 1: Cut fields 2 and 4 with comma delimiter ---")
        result1 = tool.run(file_path=test_file_rel, delimiter=",", fields="2,4")
        print(result1)

        print("\n--- Test 2: Cut characters 1 through 5 ---")
        result2 = tool.run(file_path=test_file_rel, characters="1-5")
        print(result2)

        print("\n--- Test 3: Cut fields complement (all except field 1) ---")
        result3 = tool.run(file_path=test_file_rel, delimiter=",", fields="1", complement=True)
        print(result3)

        print("\n--- Test 4: Missing fields/characters ---")
        result4 = tool.run(file_path=test_file_rel, delimiter=",")
        print(result4)

    finally:
        if os.path.exists(test_file_abs): os.remove(test_file_abs)
        print("\nCleaned up test file.")
