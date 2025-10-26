# Log Analysis Crew 📊

This crew specializes in analyzing various types of log files (e.g., web server logs, system logs, application logs) provided in CyberSkyline challenges.

## Workflow

1. **Receive Data**: The crew is initiated with crawl_data containing the challenge description, VLM markdown of log snippets or context, and log file paths (relative to /app/data).

2. **Plan Parsing & Filtering**: The Log_Parser agent determines the log format and the goal. It devises a plan using available tool wrappers (GrepTool, AwkTool, SedTool, CutTool, RegexTool, InteractiveTerminalTool) to filter, extract, and manipulate relevant log entries from the specified log file path.

3. **Identify Threats/Anomalies**: The Threat_Identifier agent analyzes the output from the parsing/filtering tools (or the raw logs if simple enough) to find suspicious activities, patterns, or anomalies (e.g., brute-force attempts, SQL injection patterns, error spikes, IOCs) that answer the challenge question.

4. **Validate Findings**: The SOC_Validator agent reviews the parsing plan (commands used via tools) and the identified threats, checking for logical consistency, command correctness, and potential false positives based on common log noise.

5. **Iterate**: If the SOC_Validator finds issues (e.g., incorrect grep pattern, misinterpreting benign bot traffic), it provides feedback. The crew refines the analysis within the ModuleAnalysisFlow.

6. **Output**: The final, validated log analysis findings (including key log lines or summaries) and the plan/commands used are saved as a markdown ticket.