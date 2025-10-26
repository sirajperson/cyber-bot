import subprocess
import shlex # For safer command parsing/splitting
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import logging
import os

logger = logging.getLogger(__name__)

# Note: Security filters (command whitelist, disallowed patterns) have been removed
# based on user request for a lab environment. This tool executes commands directly.

def execute_command_unfiltered(command_str: str, timeout: int = 120) -> str:
    """
    Executes a command string using subprocess.run with shell=True.
    Intended for controlled environments where direct shell access is required.
    Returns combined stdout and stderr.
    """
    # Split command string safely for logging purposes
    try:
        command_parts_for_log = shlex.split(command_str)
        logger.info(f"Executing unfiltered command (via shell): {command_str} (parsed as: {command_parts_for_log})")

        # Execute using shell=True
        result = subprocess.run(
            command_str, # Pass the raw string
            capture_output=True,
            text=True,
            check=False, # Don't raise exception on non-zero exit
            timeout=timeout,
            shell=True, # Execute via the system shell
            cwd="/app/data" # Run commands within the data directory context
        )
        output = f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}\nExit Code: {result.returncode}"
        return output

    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command_str}' timed out after {timeout} seconds.")
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        logger.error(f"Unexpected error executing command '{command_str}': {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"


# --- Pydantic Input Schema ---
class InteractiveTerminalToolInput(BaseModel):
    command: str = Field(..., description="The Linux command line command to execute.")

# --- Tool Definition ---
class InteractiveTerminalTool(BaseTool):
    name: str = "Interactive Terminal (Unfiltered)"
    description: str = (
        "Executes Linux commands directly in the Kali container shell within the `/app/data` directory. "
        "Maintains a short history of commands executed DURING THE CURRENT TASK. "
        "No command filtering is applied."
    )
    args_schema: Type[BaseModel] = InteractiveTerminalToolInput
    history: List[Dict[str, str]] = [] # Instance variable

    def _run(self, command: str) -> str:
        """Executes the command and returns output + history context."""
        try:
            # Execute the command without security filters
            output = execute_command_unfiltered(command)

            # Add to history (limit history size)
            self.history.append({"command": command, "output": output})
            if len(self.history) > 5:
                self.history.pop(0)

            # Format history summary
            history_summary = "\n--- Recent History (Command -> Snippet) ---\n"
            if not self.history:
                history_summary += "(No history yet in this task)\n"
            else:
                for i, entry in enumerate(self.history):
                    cmd = entry["command"]
                    output_snippet = entry["output"].replace('\n', ' ').strip()
                    if len(output_snippet) > 80:
                        output_snippet = output_snippet[:77] + "..."
                    history_summary += f"{i+1}. `{cmd}` -> {output_snippet}\n"

            # Format the final return string
            return_string = (
                f"Command Executed: `{command}`\n"
                f"--- Output ---\n"
                f"```\n{output}\n```\n"
                f"{history_summary}"
            )
            return return_string

        except Exception as e:
            # Catch unexpected errors during execution
            logger.error(f"Error running terminal tool for command '{command}': {e}", exc_info=True)
            return f"Error: An unexpected error occurred while executing the command: {e}"

# Example usage (for local testing - WILL EXECUTE ON HOST)
if __name__ == "__main__":
    terminal = InteractiveTerminalTool()
    print("--- Running tests directly on HOST OS (NOT in Docker) ---")

    print("\n--- Test 1: Basic command (echo) ---")
    result1 = terminal.run(command="echo 'Hello from host'")
    print(result1)

    print("\n--- Test 2: Another command (pwd) ---")
    result2 = terminal.run(command="pwd")
    print(result2)

    print("\n--- Test 3: Command with shell syntax (;) ---")
    result3 = terminal.run(command="echo 'First part' ; echo 'Second part'")
    print(result3)

    print("\n--- Test 4: Unknown command ---")
    result4 = terminal.run(command="nonexistentcommand12345")
    print(result4) # Should show shell error in stderr

    print("\n--- Test 5: Command with path ---")
    result5 = terminal.run(command="/bin/ls -la") # Should work on host if /bin/ls exists
    print(result5)

