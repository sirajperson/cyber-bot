#!/bin/bash
#
# create_tools.sh (Updated)
#
# This script runs from the `src/viewers/crews/tools/` directory.
# It creates the subdirectory structure for specialized tools and adds
# placeholder files for the tools identified for each crew category.
#

# --- Define Tool Categories and Specific Tools ---
# Use an associative array (Bash 4+) to map category names to tool files
# Updated to include the more comprehensive list
declare -A tool_map=(
    [binary_exploit]="ghidra_tool.py gdb_tool.py ida_pro_tool.py dnspy_tool.py ilspy_tool.py strings_tool.py binwalk_tool.py file_command_tool.py"
    [crypto]="cyberchef_tool.py online_solver_tool.py openssl_tool.py crypto_lib_tool.py frequency_analysis_tool.py"
    [forensics]="autopsy_tool.py volatility_tool.py ftk_imager_tool.py exif_tool_wrapper.py foremost_tool.py steghide_tool.py"
    [log_analysis]="grep_tool.py awk_tool.py sed_tool.py cut_tool.py regex_tool.py"
    [osint]="web_search_tool.py social_media_search_tool.py github_search_tool.py public_records_tool.py"
    [password_cracking]="hash_identifier_tool.py hashcat_tool.py john_tool.py"
    [recon]="nmap_tool.py gobuster_tool.py dirb_tool.py nikto_tool.py nuclei_tool.py"
    [traffic_analysis]="wireshark_filter_tool.py tshark_tool.py"
    [web_exploit]="sqlmap_tool.py burp_suite_tool.py curl_tool.py metasploit_tool.py xss_payload_tool.py lfi_payload_tool.py command_injection_payload_tool.py"
)

# Get the list of category names (keys of the map)
categories=("${!tool_map[@]}")
total=${#categories[@]}
count=0

echo "Starting to build $total specialized tool directories with placeholders..."
echo "This script should be run from within 'src/viewers/crews/tools/'"
echo "---"

# Create the main __init__.py for the tools package
touch "__init__.py"

# Loop through each category
for category in "${categories[@]}"; do
    ((count++))
    echo "($count/$total) Creating structure for $category tools..."

    # Create the category subdirectory
    mkdir -p "$category"

    # Create the __init__.py for the category sub-package
    touch "$category/__init__.py"

    # Get the list of tool files for this category
    IFS=' ' read -r -a tool_files <<< "${tool_map[$category]}"

    # Loop through the tool files and create them
    for tool_file in "${tool_files[@]}"; do
        # Sanitize filename slightly (remove potential command specifics)
        base_name=$(echo "$tool_file" | sed 's/_command//g') # e.g., file_command_tool.py -> file_tool.py if needed, adjust as desired
        tool_path="$category/$base_name"
        class_name=$(echo "$base_name" | sed -e 's/\(_.\)/\U\1/g' -e 's/^[a-z]/\U&/' -e 's/_//g' -e 's/\.py//g')Tool # Convert file_name.py to FileNameTool class name

        # Avoid overwriting if file exists, but ensure boilerplate
        if [[ ! -f "$tool_path" ]]; then
            echo "  - Creating $tool_path"
            # Create the file with basic BaseTool boilerplate
            cat > "$tool_path" << EOL
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# --- Input Schema (Optional) ---
# Define parameters the LLM should provide to this tool.
# Example:
# class ${class_name}Input(BaseModel):
#     target_ip: str = Field(..., description="The IP address to scan")
#     ports: Optional[str] = Field(None, description="Specific ports to scan (e.g., '80,443')")

class ${class_name}(BaseTool):
    name: str = "${class_name}"
    description: str = "Description for ${class_name}. Explain what it does and when to use it."
    # args_schema: Type[BaseModel] = ${class_name}Input # Uncomment if Input Schema is defined

    def _run(self, **kwargs: Any) -> str:
        """
        The main execution method for the tool.
        Use kwargs to access arguments defined in the Input Schema.
        """
        # --- Tool Logic Implementation ---
        # 1. Validate/Process Arguments from kwargs
        #    Example: target = kwargs.get('target_ip')
        # 2. Execute the underlying tool/command (e.g., using subprocess)
        # 3. Parse the output
        # 4. Return a descriptive string result for the LLM

        argument_str = ", ".join(f"{key}='{value}'" for key, value in kwargs.items())
        print(f"Running \${self.name} with arguments: {argument_str}")

        # Replace with actual tool implementation (e.g., call subprocess)
        # import subprocess
        # try:
        #    # Example: Run nmap
        #    # command = ["nmap", "-p", kwargs.get('ports', '-'), kwargs['target_ip']]
        #    # result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=60)
        #    # return f"Nmap scan completed:\n{result.stdout}"
        #    return f"Result from \${self.name} (Placeholder). Args: {argument_str}"
        # except Exception as e:
        #    return f"Error running \${self.name}: {e}"
        return f"Result from \${self.name} (Placeholder). Args: {argument_str}"


# Example usage (for local testing)
if __name__ == "__main__":
    tool = ${class_name}()
    # Example arguments based on a potential Input Schema:
    # result = tool.run(target_ip="127.0.0.1", ports="80")
    result = tool.run(test_arg="example") # Example without schema
    print(result)

EOL
        else
             echo "  - Skipping $tool_path (already exists)"
        fi
    done
done

echo "---"
echo "All $total tool directories and placeholder files created successfully."
echo "You can now implement the logic in each tool's '_run' method."
