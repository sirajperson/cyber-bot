import re
import logging
from typing import Type, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class RegexToolInput(BaseModel):
    """Input schema for RegexTool."""
    pattern: str = Field(..., description="The Python-compatible regular expression pattern to search for.")
    text: str = Field(..., description="The multi-line string (e.g., log snippet, file content) to search within.")
    find_all: bool = Field(True, description="If True, find all non-overlapping matches. If False, find only the first match.")
    multiline: bool = Field(False, description="Set to True to make '^' match the start of each line and '$' match the end of each line (`re.MULTILINE`).")
    ignore_case: bool = Field(False, description="Set to True for case-insensitive matching (`re.IGNORECASE`).")
    group: Optional[int] = Field(None, description="If specified (e.g., 0, 1, 2), return only the specified capturing group from each match. Group 0 is the entire match.")

class RegexTool(BaseTool):
    name: str = "Python Regex Search"
    description: str = (
        "Performs regular expression searches on provided text using Python's 're' module. "
        "Useful for extracting specific patterns (like IP addresses, timestamps, error codes) from unstructured text or log snippets. "
        "Provide the regex pattern and the text to search. Returns a list of matches or specific capture groups."
    )
    args_schema: Type[BaseModel] = RegexToolInput

    def _run(self, pattern: str, text: str, find_all: bool = True, multiline: bool = False,
             ignore_case: bool = False, group: Optional[int] = None) -> str:
        """
        Executes re.search or re.findall based on the inputs.
        """
        if not pattern: return "Error: Regex pattern cannot be empty."
        if not text: return "Error: Input text cannot be empty."

        flags = 0
        if multiline: flags |= re.MULTILINE
        if ignore_case: flags |= re.IGNORECASE

        logger.info(f"Executing regex search: pattern='{pattern}', find_all={find_all}, flags={flags}, group={group}")

        try:
            # Compile pattern for efficiency and validation
            compiled_pattern = re.compile(pattern, flags)

            matches = []
            if find_all:
                iterator = compiled_pattern.finditer(text)
                for match in iterator:
                    if group is not None:
                        try:
                            matches.append(match.group(group))
                        except IndexError:
                            return f"Error: Invalid group index {group} specified. Pattern has {match.re.groups} groups."
                    else:
                         matches.append(match.group(0)) # Default to full match
            else: # Find first match only
                match = compiled_pattern.search(text)
                if match:
                     if group is not None:
                         try:
                             matches.append(match.group(group))
                         except IndexError:
                             return f"Error: Invalid group index {group} specified. Pattern has {match.re.groups} groups."
                     else:
                          matches.append(match.group(0))

            # Format Output
            if not matches:
                return f"No matches found for pattern: '{pattern}'"
            else:
                output = f"Found {len(matches)} match(es) for pattern '{pattern}':\n"
                # Limit number of matches shown if too many
                max_matches_to_show = 50
                limited_matches = matches[:max_matches_to_show]
                output += "\n".join([f"- {m}" for m in limited_matches])
                if len(matches) > max_matches_to_show:
                    output += f"\n... (truncated, {len(matches) - max_matches_to_show} more matches found)"
                return output.strip()

        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return f"Error: Invalid regex pattern provided. Details: {e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred during regex search: {e}", exc_info=True)
            return f"An unexpected error occurred during regex search: {e}"

# Example usage
if __name__ == "__main__":
    import re # For main block
    logging.basicConfig(level=logging.INFO)
    tool = RegexTool()
    test_log = """
    INFO: Process started PID=123 User=admin Timestamp=2025-10-26T12:00:00Z
    WARN: Disk space low /dev/sda1 Usage=95% Timestamp=2025-10-26T12:02:00Z
    INFO: Process finished PID=123 Status=0 Timestamp=2025-10-26T12:05:00Z
    ERROR: Connection failed IP=192.168.1.100 Port=80 Timestamp=2025-10-26T12:10:00Z
    DEBUG: User admin logged out Timestamp=2025-10-26T12:15:00Z
    """
    print(f"--- Searching in Log Snippet:\n{test_log}---")

    print("\n--- Test 1: Find all IP addresses ---")
    # Simple IP regex
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    result1 = tool.run(pattern=ip_pattern, text=test_log)
    print(result1)

    print("\n--- Test 2: Find first timestamp (using capture group) ---")
    # Regex with a capture group for the timestamp
    ts_pattern = r'Timestamp=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)'
    result2 = tool.run(pattern=ts_pattern, text=test_log, find_all=False, group=1)
    print(result2)

    print("\n--- Test 3: Find all PIDs (capture group) ---")
    pid_pattern = r'PID=(\d+)'
    result3 = tool.run(pattern=pid_pattern, text=test_log, find_all=True, group=1)
    print(result3)

    print("\n--- Test 4: Find lines starting with WARN (multiline) ---")
    warn_pattern = r'^WARN:.*'
    result4 = tool.run(pattern=warn_pattern, text=test_log, multiline=True)
    print(result4)

    print("\n--- Test 5: Invalid Regex ---")
    result5 = tool.run(pattern="[InvalidRegex", text=test_log)
    print(result5)

    print("\n--- Test 6: Invalid Group Index ---")
    result6 = tool.run(pattern=pid_pattern, text=test_log, group=2) # Only 1 group in pattern
    print(result6)
