# Password Cracking Crew 🔓

This crew specializes in identifying hash types and devising plans to crack passwords for challenges in the CyberSkyline Password Cracking category.

## Workflow

1.  **Receive Data**: The crew gets `crawl_data` (challenge description, hash string(s), potential wordlist hints, VLM context) from the `CrewController`.
2.  **Identify Hash Type**: The `Hash_Analyst` agent analyzes the format of the provided hash(es) to determine the algorithm (e.g., MD5, SHA1, NTLM, bcrypt) and suggests the appropriate `hashcat` mode or `john` format.
3.  **Plan Cracking Strategy**: The `Cracking_Planner` agent devises an attack strategy (e.g., dictionary attack, mask attack, brute-force) based on the hash type and any contextual hints. It generates the specific command line for `hashcat` or `john`.
4.  **Validate Plan**: The `Cracking_QA` agent reviews the plan, verifying the hash identification (`hashcat` mode) and the command syntax. It ensures the chosen strategy is logical (e.g., not suggesting brute-force for a very complex hash without a mask).
5.  **Iterate**: If the `Cracking_QA` agent finds errors (e.g., incorrect mode, syntax error in command), it provides feedback. The crew refines the plan within the `ModuleAnalysisFlow`.
6.  **Output**: The final, validated password cracking plan and command(s) are saved as a markdown ticket.