# Network Traffic Analysis Crew 🌐

This crew specializes in analyzing network packet captures (`.pcap` files) for challenges in the CyberSkyline **Network Traffic Analysis** category.

## Workflow

1.  **Receive Data**: The crew gets `crawl_data` (challenge description, VLM context, link to or description of a `.pcap` file) from the `CrewController`.
2.  **Plan Analysis**: The `Pcap_Analyst` agent determines the goal (e.g., find credentials, extract a file, identify malicious traffic) and suggests appropriate `tshark` or `Wireshark` display filters or specific `tshark` commands to isolate relevant packets or extract data.
3.  **Validate Plan**: The `NetSec_Verifier` agent reviews the analysis plan, ensuring the suggested filters or commands are correct, efficient, and relevant to the challenge objective. It checks for common filter syntax errors or logical flaws.
4.  **Iterate**: If the `NetSec_Verifier` finds issues (e.g., suggesting a filter that won't capture the needed protocol), it provides feedback. The crew refines the plan within the `ModuleAnalysisFlow`.
5.  **Output**: The final, validated traffic analysis plan, including specific filters or commands, is saved as a markdown ticket.