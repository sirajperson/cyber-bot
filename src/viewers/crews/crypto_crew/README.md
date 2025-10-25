# Crypto Crew 🔐

This crew specializes in analyzing and solving cryptographic challenges found in CyberSkyline modules.

## Workflow

1.  **Receive Data**: The crew receives `crawl_data` (including VLM markdown describing the challenge, ciphertext, and any hints) from the `CrewController`.
2.  **Identify Cipher**: The `Cipher_Identifier` agent analyzes the ciphertext and context to determine the encryption method (e.g., classical ciphers like Caesar/Vigenere, modern block ciphers, encoding schemes like Base64).
3.  **Plan Decryption**: The `Crypto_Solver` agent suggests specific tools (like CyberChef, `cryptii`, `hashcat` for certain hashes used as keys) or Python libraries/scripts to perform the decryption based on the identified cipher.
4.  **Validate Plan**: The `Crypto_Verifier` agent reviews the plan, checking if the identified cipher is plausible and if the suggested tool/method is correct.
5.  **Iterate**: If the `Crypto_Verifier` finds issues, it provides feedback (e.g., "Feedback: The text appears to be Base64 encoded first, then encrypted with Vigenere. Update the plan to include a decoding step."). The crew then refines the plan within the `ModuleAnalysisFlow`.
6.  **Output**: The final, validated decryption plan is saved as a markdown ticket.# Crypto Crew 🔐

This crew specializes in analyzing and solving cryptographic challenges found in CyberSkyline modules.

## Workflow

1.  **Receive Data**: The crew receives `crawl_data` (including VLM markdown describing the challenge, ciphertext, and any hints) from the `CrewController`.
2.  **Identify Cipher**: The `Cipher_Identifier` agent analyzes the ciphertext and context to determine the encryption method (e.g., classical ciphers like Caesar/Vigenere, modern block ciphers, encoding schemes like Base64).
3.  **Plan Decryption**: The `Crypto_Solver` agent suggests specific tools (like CyberChef, `cryptii`, `hashcat` for certain hashes used as keys) or Python libraries/scripts to perform the decryption based on the identified cipher.
4.  **Validate Plan**: The `Crypto_Verifier` agent reviews the plan, checking if the identified cipher is plausible and if the suggested tool/method is correct.
5.  **Iterate**: If the `Crypto_Verifier` finds issues, it provides feedback (e.g., "Feedback: The text appears to be Base64 encoded first, then encrypted with Vigenere. Update the plan to include a decoding step."). The crew then refines the plan within the `ModuleAnalysisFlow`.
6.  **Output**: The final, validated decryption plan is saved as a markdown ticket.