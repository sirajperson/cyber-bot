import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Configuration ---
# Adjust if Volatility isn't in PATH or uses a specific python version
VOLATILITY_CMD = os.getenv("VOLATILITY_CMD", "vol") # Command to run Volatility 3 (e.g., 'vol', 'python /path/to/vol.py')

# --- Input Schema ---
class VolatilityToolInput(BaseModel):
    """Input schema for VolatilityTool."""
    memory_image_path: str = Field(..., description="Path to the memory image file (e.g., .vmem, .raw, .dmp), relative to '/app/data'.")
    plugin: str = Field(..., description="The Volatility 3 plugin to run (e.g., 'windows.pslist', 'linux.bash', 'imageinfo').")
    plugin_options: Optional[str] = Field("", description="Additional options/arguments to pass to the specified plugin (e.g., '--pid 1234', '--dump').")

class VolatilityTool(BaseTool):
    name: str = "Volatility 3 Runner"
    description: str = (
        f"Executes a Volatility 3 plugin against a memory image file to perform memory forensics. "
        f"Specify the memory image path (relative to '/app/data'), the plugin name (e.g., 'windows.pslist', 'linux.bash'), "
        f"and any plugin-specific options. Uses the command '{VOLATILITY_CMD}'. "
        "Returns the output of the plugin."
    )
    args_schema: Type[BaseModel] = VolatilityToolInput

    def _run(self, memory_image_path: str, plugin: str, plugin_options: Optional[str] = "") -> str:
        """
        Executes the specified Volatility 3 command.
        """
        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', memory_image_path.lstrip('/'))).lstrip('/')
        target_image_file = os.path.abspath(os.path.join(base_dir, relative_path))

        if not target_image_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {memory_image_path}")
            return f"Error: Invalid memory image path '{memory_image_path}'. Path must be within the data directory."
        if not os.path.isfile(target_image_file):
             logger.error(f"Memory image not found for Volatility: '{target_image_file}'")
             return f"Error: Memory image file not found at '{target_image_file}'."

        # Basic sanitization/validation for plugin name (prevent command injection if VOLATILITY_CMD includes python)
        # Allow dots and alphanumeric for plugin names like windows.pslist
        if not re.match(r'^[\w\.]+$', plugin):
            logger.error(f"Invalid characters in plugin name: '{plugin}'")
            return f"Error: Invalid plugin name '{plugin}'. Only alphanumeric characters and dots are allowed."

        # --- Construct Command ---
        command = [VOLATILITY_CMD]
        # Add global options first if any needed by default, e.g. -q for quiet?
        command.extend(["-f", target_image_file]) # Specify the memory image file
        command.append(plugin) # Add the plugin name

        # Add plugin options safely
        if plugin_options:
            # Use shlex to split options respecting quotes, but execute as list
            try:
                options_list = shlex.split(plugin_options)
                command.extend(options_list)
            except ValueError as e:
                logger.error(f"Could not parse plugin options '{plugin_options}': {e}")
                return f"Error: Could not parse plugin options: {e}. Check quoting."


        logger.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")

        # --- Execute Command ---
        try:
            # Volatility can take a long time and produce large output
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors='ignore', # Ignore potential decoding errors in output
                check=False,
                timeout=600 # 10 minutes timeout
            )

            # --- Process Output ---
            output = f"Volatility 3 execution ('{plugin}') on '{memory_image_path}':\n"
            # Volatility prints results to stdout, errors/info usually to stderr
            if result.stdout:
                output += f"--- Plugin Output (stdout) ---\n```\n{result.stdout.strip()}\n```\n"
            else:
                 output += "--- Plugin Output (stdout) ---\n(No standard output from plugin)\n"

            if result.stderr:
                 # Filter common Volatility INFO/DEBUG lines if desired
                 filtered_stderr = "\n".join(line for line in result.stderr.splitlines() if not line.startswith(('INFO:', 'DEBUG:')))
                 if filtered_stderr.strip():
                      output += f"--- Volatility Log/Error (stderr) ---\n{filtered_stderr.strip()}\n"

            output += f"Exit Code: {result.returncode}\n"

            if result.returncode != 0:
                 logger.error(f"Volatility command failed for {target_image_file}, plugin {plugin}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                 output += "\nError: Volatility command failed. Check stderr output above for details (e.g., plugin not found, image format error, plugin error)."
            else:
                 logger.info(f"Volatility command successful for {target_image_file}, plugin {plugin}.")


            max_len = 10000 # Allow larger output for Volatility
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Volatility command timed out for file '{memory_image_path}', plugin '{plugin}'.")
            return f"Error: Volatility command timed out on '{memory_image_path}' with plugin '{plugin}'."
        except FileNotFoundError:
            logger.error(f"'{VOLATILITY_CMD}' command not found. Is Volatility 3 installed and configured?")
            return f"Error: '{VOLATILITY_CMD}' command not found. Ensure Volatility 3 is installed and accessible."
        except Exception as e:
            logger.error(f"Error running Volatility on '{memory_image_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running Volatility: {e}"

# Example usage (requires Volatility 3 installed as 'vol' and a memory image)
if __name__ == "__main__":
    import re # Need re for main block
    logging.basicConfig(level=logging.INFO)
    tool = VolatilityTool()

    # --- Setup: Point to a test memory image ---
    # !!! Replace this with the actual RELATIVE path (to /app/data) of a test memory image !!!
    # You'll need to place a memory image (e.g., from challenges or CTFs) into the ./data directory
    test_image_relative = "example_memory_image.vmem" # <-- CHANGE THIS
    # ----------------------------------------------

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    test_image_abs = os.path.join(data_dir_abs, test_image_relative)

    vol_exists = any(os.access(os.path.join(path, VOLATILITY_CMD), os.X_OK) for path in os.environ["PATH"].split(os.pathsep))
    image_exists = os.path.isfile(test_image_abs)

    if vol_exists and image_exists:
        print(f"--- Testing Volatility Tool on '{test_image_relative}' ---")

        print("\n--- Test 1: Run imageinfo ---")
        result1 = tool.run(memory_image_path=test_image_relative, plugin="imageinfo")
        print(result1)

        # Try to guess OS from imageinfo to run a relevant plugin
        os_plugin = "linux.pslist" # Default guess
        if "windows" in result1.lower():
             os_plugin = "windows.pslist"

        print(f"\n--- Test 2: Run {os_plugin} ---")
        result2 = tool.run(memory_image_path=test_image_relative, plugin=os_plugin)
        print(result2)

        print("\n--- Test 3: Plugin with options (Example: dump files) ---")
        # This plugin/option might not work on all images, just a syntax test
        dump_plugin = "windows.dumpfiles" if "windows" in result1.lower() else "linux.dump_files" # Adjust plugin name
        # Note: Dumping requires an output dir, Volatility handles this itself usually
        result3 = tool.run(memory_image_path=test_image_relative, plugin=dump_plugin, plugin_options="--virtaddr 0xADDRESS_HERE") # Needs a real address
        print(result3) # Expect error if address invalid

    else:
        print("\n--- Skipping Volatility execution tests ---")
        if not vol_exists: print(f"  - '{VOLATILITY_CMD}' command not found in PATH.")
        if not image_exists: print(f"  - Test memory image '{test_image_abs}' not found. Please place one in ./data")

    print("\n--- Test 4: Non-existent image file ---")
    result4 = tool.run(memory_image_path="nosuchimage.vmem", plugin="imageinfo")
    print(result4)
