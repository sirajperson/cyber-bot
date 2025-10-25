# Recon Crew 🗺️

This crew specializes in planning and validating network scanning and reconnaissance operations for challenges in the CyberSkyline **Scanning & Reconnaissance** category.

## Workflow

1.  **Receive Data**: The crew gets `crawl_data` (challenge description, target IP/domain, VLM context) from the `CrewController`.
2.  **Plan Reconnaissance**: The `Recon_Planner` agent analyzes the target information and challenge goal. It devises a phased plan, suggesting appropriate tools like `nmap` for port scanning, `gobuster` or `dirb` for web directory enumeration, and `nikto` or `nuclei` for vulnerability scanning. It specifies command-line options.
3.  **Validate Plan**: The `PenTest_Lead` agent reviews the reconnaissance plan for logical flow, efficiency, and correctness. It ensures that scans are ordered appropriately (e.g., port scan before web scan) and that tool usage is correct.
4.  **Iterate**: If the `PenTest_Lead` finds issues (e.g., suggesting a web scan before confirming a web server exists), it provides feedback. The crew refines the plan within the `ModuleAnalysisFlow`.
5.  **Output**: The final, validated reconnaissance plan, including specific commands, is saved as a markdown ticket.