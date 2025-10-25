# OSINT Crew 🕵️

This crew specializes in gathering and analyzing Open Source Intelligence (OSINT) for challenges in the CyberSkyline OSINT category.

## Workflow

1.  **Receive Data**: The crew gets `crawl_data` (challenge description, target names/domains, VLM context) from the `CrewController`.
2.  **Plan Intelligence Gathering**: The `Public_Data_Miner` agent identifies key search terms and plans how to use OSINT tools (search engines, social media, public records, code repositories) to gather relevant information about the target.
3.  **Synthesize Findings**: The agent (or a dedicated synthesizer agent, if needed) compiles the gathered information into a coherent report addressing the challenge question.
4.  **Validate Findings**: The `OSINT_Validator` agent reviews the gathered intelligence and the plan, ensuring the information is relevant, properly sourced (where possible), and directly answers the challenge question. It checks for assumptions or leaps in logic.
5.  **Iterate**: If the `OSINT_Validator` finds issues (e.g., information is too generic, doesn't answer the specific question), it provides feedback. The crew refines its search and analysis within the `ModuleAnalysisFlow`.
6.  **Output**: The final, validated OSINT findings are saved as a markdown ticket.