#!/bin/bash
#
# create_crews.sh
#
# This script runs from the `src/viewers/crews/` directory.
# It creates the full directory and file structure for the 9 specialized
# challenge crews, following the `game_builder_crew` pattern.
#

# Define the list of crews based on the 9 challenge categories
crews=(
    "osint_crew"
    "crypto_crew"
    "password_cracking_crew"
    "log_analysis_crew"
    "traffic_analysis_crew"
    "forensics_crew"
    "recon_crew"
    "web_exploit_crew"
    "binary_exploit_crew"
)

# Get the total number of crews
total=${#crews[@]}
count=0

echo "Starting to build $total specialized crew structures..."
echo "This script should be run from within 'src/viewers/crews/'"
echo "---"

# Loop through each crew name and create its structure
for crew_name in "${crews[@]}"; do
    ((count++))
    echo "($count/$total) Creating structure for $crew_name..."

    # Create the main crew directory and its config subdirectory
    # The -p flag ensures no error if the directory already exists
    mkdir -p "$crew_name/config"

    # Create the core files for each crew
    # This mirrors the 'game_builder_crew' structure
    touch "$crew_name/__init__.py"
    touch "$crew_name/crew.py"
    touch "$crew_name/README.md"
    touch "$crew_name/config/agents.yaml"
    touch "$crew_name/config/tasks.yaml"

    # Optional: Add a placeholder title to the new README
    echo "# $crew_name" > "$crew_name/README.md"
    echo "Placeholder for $crew_name documentation." >> "$crew_name/README.md"

done

echo "---"
echo "All $total crew structures have been created successfully."
echo "You can now populate the 'crew.py' and YAML files for each crew."