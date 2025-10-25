# Forensics Crew 💾

This crew specializes in analyzing digital evidence for challenges in the CyberSkyline Forensics category.

## Workflow

1.  **Receive Data**: The crew gets `crawl_data` (including VLM markdown, screenshots, and descriptions of files like disk images, memory dumps, images, or documents) from the `CrewController`.
2.  **Identify Evidence Type**: The `File_Analyst` agent determines the type of digital evidence provided (e.g., `.dd` image, `.vmem` dump, `.jpg`, `.pdf`) and the likely forensic technique required (e.g., file carving, metadata analysis, steganography, memory analysis).
3.  **Plan Analysis**: The `Forensics_Planner` agent suggests specific tools (like `Autopsy`, `Volatility`, `exiftool`, `binwalk`, `steghide`, `foremost`) and steps to analyze the evidence and extract the flag.
4.  **Validate Plan**: The `Evidence_Validator` agent reviews the plan, ensuring the tool selection matches the file type and the analysis steps are logical for the suspected technique.
5.  **Iterate**: If the `Evidence_Validator` finds flaws (e.g., suggesting Volatility for a disk image), it provides feedback. The crew refines the plan within the `ModuleAnalysisFlow`.
6.  **Output**: The final, validated forensic analysis plan is saved as a markdown ticket.