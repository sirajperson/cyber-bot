import subprocess
import os
import logging
import shlex
import re # For basic pattern validation
from typing import Type, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class GrepToolInput(BaseModel):
    """Input schema for GrepTool."""
    pattern: str = Field(..., description="The pattern (string or basic regex) to search for.")
    file_path: str = Field(..., description="The path to the input file to search within, relative to the '/app/data' directory.")
    ignore_case: bool = Field(False, description="Perform case-insensitive matching ('-i' flag).")
    invert_match: bool = Field(False, description="Select non-matching lines ('-v' flag).")
    count_matches: bool = Field(False, description="Print only a count of matching lines ('-c' flag).")
    max_count: Optional[int] = Field(None, description="Stop reading after NUM matching lines ('-m NUM' flag).")
    extra_args: Optional[str] = Field("", description="Any additional grep command line arguments (e.g., '-A 2' for context). Use with caution.")

class GrepTool(BaseTool):
    name: str = "Grep Text Search"
    description: str = (
        "Searches for a specified pattern within a text file using the 'grep' command. "
        "Useful for filtering log files or any text data based on keywords or simple regex. "
        "Provide the pattern, the file path (relative to '/app/data'), and optional flags like ignore_case or invert_match."
    )
    args_schema: Type[BaseModel] = GrepToolInput

    def _run(self, pattern: str, file_path: str, ignore_case: bool = False, invert_match: bool = False,
             count_matches: bool = False, max_count: Optional[int] = None, extra_args: Optional[str] = "") -> str:
        """
        Executes the 'grep' command.
        """
        # --- Basic Pattern Safety (Very Limited) ---
        # Avoid patterns starting with '-' to prevent treating them as options
        if pattern.startswith('-'):
            return f"Error: Pattern '{pattern}' starts with '-'. This is disallowed for safety."

        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', file_path.lstrip('/'))).lstrip('/')
        target_file = os.path.abspath(os.path.join(base_dir, relative_path))

        if not target_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {file_path}")
            return f"Error: Invalid file path '{file_path}'. Path must be within the data directory."
        if not os.path.isfile(target_file):
            logger.error(f"Input file not found for grep: '{target_file}'")
            return f"Error: File not found at '{target_file}'."

        # --- Construct Command ---
        command = ["grep"]
        if ignore_case: command.append("-i")
        if invert_match: command.append("-v")
        if count_matches: command.append("-c")
        if max_count is not None and max_count > 0: command.extend(["-m", str(max_count)])

        if extra_args:
            try:
                 # Filter potentially unsafe/redundant args from extra_args
                 forbidden_extra = {'-e', '-f', '-i', '-v', '-c', '-m'} # Prevent overriding core args
                 parsed_extra = shlex.split(extra_args)
                 safe_extra = [arg for arg in parsed_extra if arg not in forbidden_extra and not arg.startswith(('-e','-f'))] # Also block combined flags
                 if len(safe_extra) != len(parsed_extra):
                      logger.warning(f"Some extra_args were filtered for safety/redundancy: Original='{extra_args}', Used='{' '.join(safe_extra)}'")
                 command.extend(safe_extra)
            except ValueError as e:
                logger.error(f"Could not parse extra_args '{extra_args}': {e}")
                return f"Error: Could not parse extra_args: {e}. Check quoting."

        # Add pattern and file path last
        command.append(pattern)
        command.append(target_file)

        logger.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")

        # --- Execute Command ---
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors='ignore',
                check=False, # Grep exits 1 if no lines selected, 2 for errors
                timeout=60
            )

            # --- Process Output ---
            output = f"Grep search result for pattern '{pattern}' in '{file_path}':\n"
            if result.stdout:
                output += f"--- Matches Found (stdout) ---\n```\n{result.stdout.strip()}\n```\n"
            else:
                 # Check exit code to distinguish "no match" from errors
                 if result.returncode == 1:
                     output += "--- Matches Found (stdout) ---\n(No matching lines found)\n"
                 else: # Likely an error if stdout empty and exit code not 0 or 1
                     output += "--- Matches Found (stdout) ---\n(No standard output, check stderr)\n"

            if result.stderr:
                output += f"--- stderr ---\n{result.stderr.strip()}\n"
            output += f"Exit Code: {result.returncode} (0=OK, 1=No Match, >1=Error)\n"

            if result.returncode > 1:
                logger.error(f"Grep command failed for {target_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                output += "\nError: Grep command failed. Check pattern syntax or file access."
            elif result.returncode == 1:
                 logger.info(f"Grep search completed for {target_file}, no matches found.")
            else:
                 logger.info(f"Grep search successful for {target_file}.")


            max_len = 5000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Grep command timed out for file '{file_path}'.")
            return f"Error: Grep command timed out on '{file_path}'."
        except FileNotFoundError:
            logger.error("'grep' command not found.")
            return "Error: 'grep' command not found."
        except Exception as e:
            logger.error(f"Error running grep on '{file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running grep: {e}"

# Example usage (requires grep and a test file)
if __name__ == "__main__":
    import re # For main block
    logging.basicConfig(level=logging.INFO)
    tool = GrepTool()
    # Create dummy data file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)
    test_file_rel = "test_grep.log"
    test_file_abs = os.path.join(data_dir_abs, test_file_rel)
    try:
        with open(test_file_abs, "w") as f:
            f.write("INFO: Process started PID=123 User=admin\n")
            f.write("WARN: Disk space low /dev/sda1 Usage=95%\n")
            f.write("info: Process finished PID=123 Status=0\n") # Lowercase info
            f.write("ERROR: Connection failed IP=192.168.1.100 Port=80\n")
            f.write("DEBUG: User admin logged out\n")
        print(f"Created dummy log file: {test_file_abs}")

        print("\n--- Test 1: Find 'ERROR' (case-sensitive) ---")
        result1 = tool.run(file_path=test_file_rel, pattern="ERROR")
        print(result1)

        print("\n--- Test 2: Find 'info' (case-insensitive) ---")
        result2 = tool.run(file_path=test_file_rel, pattern="info", ignore_case=True)
        print(result2)

        print("\n--- Test 3: Count lines containing 'PID=' ---")
        result3 = tool.run(file_path=test_file_rel, pattern="PID=", count_matches=True)
        print(result3)

        print("\n--- Test 4: Invert match (lines NOT containing 'admin') ---")
        result4 = tool.run(file_path=test_file_rel, pattern="admin", invert_match=True)
        print(result4)

        print("\n--- Test 5: No match found ---")
        result5 = tool.run(file_path=test_file_rel, pattern="NoSuchStringHere")
        print(result5) # Should show Exit Code 1

        print("\n--- Test 6: Invalid regex pattern ---")
        result6 = tool.run(file_path=test_file_rel, pattern="[InvalidRegex") # Malformed regex
        print(result6) # Should show Exit Code > 1 and stderr

    finally:
        if os.path.exists(test_file_abs): os.remove(test_file_abs)
        print("\nCleaned up test file.")
