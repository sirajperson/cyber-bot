import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class AwkToolInput(BaseModel):
    """Input schema for AwkTool."""
    awk_script: str = Field(..., description="The AWK script/program to execute (e.g., '{print $1, $NF}'). Should be properly quoted if necessary for the shell.")
    file_path: str = Field(..., description="The path to the input file to process, relative to the '/app/data' directory.")
    field_separator: Optional[str] = Field(None, description="Specify the input field separator ('-F' option). E.g., '-F:' or '-F\\t'.")

class AwkTool(BaseTool):
    name: str = "AWK Text Processor"
    description: str = (
        "Processes text files line by line using AWK patterns and actions. "
        "Excellent for extracting specific columns/fields, performing calculations, or filtering based on field content. "
        "Provide the AWK script, the input file path (relative to '/app/data'), and optionally a field separator."
    )
    args_schema: Type[BaseModel] = AwkToolInput

    def _run(self, awk_script: str, file_path: str, field_separator: Optional[str] = None) -> str:
        """
        Executes the 'awk' command.
        """
        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', file_path.lstrip('/'))).lstrip('/')
        target_file = os.path.abspath(os.path.join(base_dir, relative_path))

        if not target_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {file_path}")
            return f"Error: Invalid file path '{file_path}'. Path must be within the data directory."
        if not os.path.isfile(target_file):
            logger.error(f"Input file not found for awk: '{target_file}'")
            return f"Error: File not found at '{target_file}'."

        # --- Construct Command ---
        command = ["awk"]
        if field_separator:
            # Pass separator carefully
            command.extend(["-F", field_separator])

        # Add the script. Pass it as a single argument.
        command.append(awk_script)

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
            output = f"AWK execution result for '{file_path}' with script '{awk_script}':\n"
            if result.stdout:
                output += f"--- stdout ---\n```\n{result.stdout.strip()}\n```\n"
            else:
                output += "--- stdout ---\n(No standard output generated)\n"
            if result.stderr:
                output += f"--- stderr ---\n{result.stderr.strip()}\n"
            output += f"Exit Code: {result.returncode}\n"

            if result.returncode != 0:
                logger.error(f"AWK command failed for {target_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                output += "\nError: AWK command failed. Check script syntax and file format."

            max_len = 5000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"AWK command timed out for file '{file_path}'.")
            return f"Error: AWK command timed out on '{file_path}'."
        except FileNotFoundError:
            logger.error("'awk' command not found.")
            return "Error: 'awk' command not found."
        except Exception as e:
            logger.error(f"Error running awk on '{file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running awk: {e}"

# Example usage (requires awk and a test file)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = AwkTool()
    # Create dummy data file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)
    test_file_rel = "test_awk.log"
    test_file_abs = os.path.join(data_dir_abs, test_file_rel)
    try:
        with open(test_file_abs, "w") as f:
            f.write("INFO: Process started PID=123 User=admin\n")
            f.write("WARN: Disk space low /dev/sda1 Usage=95%\n")
            f.write("INFO: Process finished PID=123 Status=0\n")
            f.write("ERROR: Connection failed IP=192.168.1.100 Port=80\n")
        print(f"Created dummy log file: {test_file_abs}")

        print("\n--- Test 1: Print first and last field ---")
        result1 = tool.run(file_path=test_file_rel, awk_script='{print $1, $NF}')
        print(result1)

        print("\n--- Test 2: Filter lines containing 'ERROR' and print all fields ---")
        result2 = tool.run(file_path=test_file_rel, awk_script='/ERROR/ {print $0}')
        print(result2)

        print("\n--- Test 3: Use field separator on ERROR line ---")
        # Example: Get IP address (assuming space and = are separators)
        result3 = tool.run(file_path=test_file_rel, awk_script="/ERROR/ {print $3}", field_separator="[ =]") # Use regex separator
        print(result3) # Should print IP=192.168.1.100

        print("\n--- Test 4: Syntax error in script ---")
        result4 = tool.run(file_path=test_file_rel, awk_script='{print $1') # Missing closing brace
        print(result4)

    finally:
        if os.path.exists(test_file_abs): os.remove(test_file_abs)
        print("\nCleaned up test file.")
