# Forensics Crew 💾

This crew specializes in analyzing digital evidence for challenges in the CyberSkyline Forensics category, such as disk images, memory dumps, images, documents, or network captures.

## Workflow

1. **Receive Data**: The crew gets crawl_data (challenge description, VLM context, file paths relative to /app/data) from the CrewController.

2. **Identify Evidence Type & Technique**: The File_Analyst agent uses FileTool (from binary_exploit tools) to determine the evidence type (e.g., .dd, .vmem, .jpg, .pdf, .pcap) and hypothesizes the required forensic technique (file carving, metadata analysis, steganography, memory analysis, network protocol analysis).

3. **Plan Analysis**: The Forensics_Planner agent selects and plans the use of specific tools based on the identified type and technique:
   * **Metadata**: Uses ExifToolWrapper for image/document metadata.
   * **Steganography**: Uses SteghideTool (for common image/audio stego) or BinwalkTool (for embedded files).
   * **File Carving**: Uses ForemostTool to recover deleted files from images.
   * **Memory Analysis**: Uses VolatilityTool (providing instructions/commands for Volatility 3).
   * **Disk Image Analysis**: Provides instructions for AutopsyTool or FTKImagerTool (GUI-based).
   * **Network Analysis**: Uses TsharkTool (from traffic_analysis tools) if the evidence is a .pcap file.
   * **General**: Uses StringsTool or InteractiveTerminalTool for basic checks.

4. **Validate Plan**: The Evidence_Validator agent reviews the plan, ensuring the tool selection (ExifToolWrapper, SteghideTool, VolatilityTool, etc.) matches the file type and the analysis steps are logical.

5. **Iterate**: If the Evidence_Validator finds flaws (e.g., suggesting Volatility for a disk image, incorrect steghide parameters), it provides feedback. The crew refines the plan within the ModuleAnalysisFlow.

6. **Output**: The final, validated forensic analysis plan (including initial findings and steps/commands) is saved as a markdown ticket.