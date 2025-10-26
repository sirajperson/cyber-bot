import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class TsharkToolInput(BaseModel):
    """Input schema for TsharkTool."""
    pcap_file_path: str = Field(..., description="Path to the network capture file (.pcap, .pcapng) to analyze, relative to '/app/data'.")
    display_filter: Optional[str] = Field(None, description="Wireshark display filter to apply (e.g., 'http.request.method == \"GET\"', 'tcp.port == 80'). Use '-Y' option.")
    read_filter: Optional[str] = Field(None, description="Capture filter syntax filter to apply while reading ('-R' option). Less common for saved files.")
    fields: Optional[List[str]] = Field(None, description="List of specific fields to extract (e.g., ['ip.src', 'ip.dst', 'tcp.port']). Uses '-T fields -e ...' options.")
    extra_args: Optional[str] = Field("", description="Any additional tshark command line arguments (e.g., '-z io,stat,1', '--export-objects http,dest_dir'). Use with caution. Do not include '-r', '-Y', '-R', '-T fields', or '-e'.")
    packet_count: Optional[int] = Field(50, description="Maximum number of packets to display ('-c' flag). Set to 0 or None for unlimited (may produce large output). Default is 50.")

class TsharkTool(BaseTool):
    name: str = "Tshark Packet Analyzer"
    description: str = (
        "Analyzes network capture files (.pcap, .pcapng) using the 'tshark' command-line utility. "
        "Can apply display filters, read filters, extract specific fields, or run other tshark operations. "
        "Operates on files within the '/app/data' directory. Specify the pcap file path relative to '/app/data'. "
        "Returns the standard output of the tshark command."
    )
    args_schema: Type[BaseModel] = TsharkToolInput

    def _run(self, pcap_file_path: str, display_filter: Optional[str] = None, read_filter: Optional[str] = None,
             fields: Optional[List[str]] = None, extra_args: Optional[str] = "", packet_count: Optional[int] = 50) -> str:
        """
        Executes the 'tshark' command with specified options.
        """
        # --- Security/Context Check ---
        base_dir = "/app/data"
        relative_path = os.path.normpath(os.path.join('/', pcap_file_path.lstrip('/'))).lstrip('/')
        target_pcap_file = os.path.abspath(os.path.join(base_dir, relative_path))

        if not target_pcap_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: {pcap_file_path}")
            return f"Error: Invalid pcap file path '{pcap_file_path}'. Path must be within the data directory."
        if not os.path.isfile(target_pcap_file):
             logger.error(f"Pcap file not found for tshark: '{target_pcap_file}'")
             return f"Error: Pcap file not found at '{target_pcap_file}'."

        # --- Construct Command ---
        command = ["tshark", "-r", target_pcap_file] # Read from file

        if packet_count is not None and packet_count > 0:
            command.extend(["-c", str(packet_count)])

        if display_filter:
            # Use -Y for display filter. Argument needs careful quoting if passed via list.
            # Using shlex.split on the filter itself might be needed if complex.
            # For simplicity now, we assume agent provides a single filter string.
            command.extend(["-Y", display_filter])

        if read_filter:
            command.extend(["-R", read_filter])

        if fields:
            command.append("-Tfields")
            for field in fields:
                # Basic validation: ensure field name seems reasonable (alphanumeric, dots, underscores)
                if re.match(r'^[\w\.]+$', field):
                    command.extend(["-e", field])
                else:
                    logger.warning(f"Skipping potentially unsafe field name: '{field}'")
                    # Optionally return an error instead of skipping

        if extra_args:
            # Split extra args respecting quotes
            try:
                # Disallow certain args for safety/redundancy?
                forbidden_extra = {'-r', '-Y', '-R', '-Tfields', '-e', '-c'}
                parsed_extra = shlex.split(extra_args)
                safe_extra = [arg for arg in parsed_extra if arg not in forbidden_extra]
                if len(safe_extra) != len(parsed_extra):
                     logger.warning(f"Some extra_args were filtered for safety/redundancy: Original='{extra_args}', Used='{' '.join(safe_extra)}'")
                command.extend(safe_extra)
            except ValueError as e:
                logger.error(f"Could not parse extra_args '{extra_args}': {e}")
                return f"Error: Could not parse extra_args: {e}. Check quoting."


        logger.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")

        # --- Execute Command ---
        try:
            # Tshark can produce large output and take time
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors='ignore', # Ignore decoding errors in packet data
                check=False,
                timeout=180 # 3 minutes timeout
            )

            # --- Process Output ---
            output = f"Tshark analysis result for '{pcap_file_path}':\n"
            if result.stdout:
                output += f"--- stdout ---\n```\n{result.stdout.strip()}\n```\n"
            else:
                 output += "--- stdout ---\n(No standard output generated)\n"

            if result.stderr:
                # Filter common non-error stderr messages if needed
                filtered_stderr = "\n".join(line for line in result.stderr.splitlines() if "packets captured" not in line)
                if filtered_stderr.strip():
                     output += f"--- stderr ---\n{filtered_stderr.strip()}\n"

            output += f"Exit Code: {result.returncode}\n"

            if result.returncode != 0:
                 logger.error(f"Tshark command failed for {target_pcap_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                 output += "\nError: Tshark command failed. Check stderr output above for details (e.g., filter syntax error, file format error)."
            else:
                 logger.info(f"Tshark command successful for {target_pcap_file}.")

            # Limit output length
            max_len = 10000 # Allow larger output for Tshark
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"Tshark command timed out for file '{pcap_file_path}'.")
            return f"Error: Tshark command timed out on '{pcap_file_path}'."
        except FileNotFoundError:
            logger.error("'tshark' command not found. Is it installed?")
            return "Error: 'tshark' command not found."
        except Exception as e:
            logger.error(f"Error running tshark on '{pcap_file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running tshark: {e}"

# Example usage (requires tshark and a sample pcap file in ./data)
if __name__ == "__main__":
    import re # Import re for main block if not already imported
    logging.basicConfig(level=logging.INFO)
    tool = TsharkTool()

    # --- Setup: Point to a test pcap file ---
    # !!! Replace this with the actual RELATIVE path (to /app/data) of a test pcap file !!!
    # You'll need to place a sample pcap (e.g., from Wireshark samples) into the ./data directory
    test_pcap_relative = "sample.pcap" # <-- CHANGE THIS if needed
    # ----------------------------------------------

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    test_pcap_abs = os.path.join(data_dir_abs, test_pcap_relative)

    tshark_exists = any(os.access(os.path.join(path, "tshark"), os.X_OK) for path in os.environ["PATH"].split(os.pathsep))
    pcap_exists = os.path.isfile(test_pcap_abs)

    if tshark_exists and pcap_exists:
        print(f"--- Testing Tshark Tool on '{test_pcap_relative}' ---")

        print("\n--- Test 1: Read first 5 packets ---")
        result1 = tool.run(pcap_file_path=test_pcap_relative, packet_count=5)
        print(result1)

        print("\n--- Test 2: Apply display filter (e.g., http) ---")
        result2 = tool.run(pcap_file_path=test_pcap_relative, display_filter="http", packet_count=10)
        print(result2)

        print("\n--- Test 3: Extract specific fields (IP src/dst) ---")
        result3 = tool.run(pcap_file_path=test_pcap_relative, fields=["ip.src", "ip.dst"], packet_count=10)
        print(result3)

        print("\n--- Test 4: Using extra args (e.g., packet counts summary) ---")
        # Example: Protocol hierarchy stats. Be careful with args.
        result4 = tool.run(pcap_file_path=test_pcap_relative, extra_args="-qz io,phs", packet_count=None) # -q for quiet, -z for stats
        print(result4)

    else:
        print("\n--- Skipping Tshark execution tests ---")
        if not tshark_exists: print(f"  - 'tshark' command not found in PATH.")
        if not pcap_exists: print(f"  - Test pcap file '{test_pcap_abs}' not found. Please place one in ./data")

    print("\n--- Test 5: Non-existent pcap file ---")
    result5 = tool.run(pcap_file_path="nosuchfile.pcapng")
    print(result5)
