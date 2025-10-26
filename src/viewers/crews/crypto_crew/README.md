# Crypto Crew 🔐

This crew specializes in analyzing and solving cryptographic challenges found in CyberSkyline modules.

## Workflow

1. **Receive Data**: The crew receives crawl_data (including VLM markdown describing the challenge, ciphertext, and any hints) from the CrewController.

2. **Identify Cipher**: The Cipher_Identifier agent analyzes the ciphertext and context. It utilizes tools like FrequencyAnalysisTool (for classical ciphers) and CryptoLibTool (for detecting common encodings like Base64/Hex) to determine the encryption method.

3. **Plan Decryption**: The Crypto_Solver agent takes the identified cipher. It then uses appropriate tools to generate a solution plan:
   * **CryptoLibTool**: For executing Base64/Hex decoding.
   * **OpensslTool**: For executing decryption commands (e.g., AES) based on provided keys/IVs/passphrases.
   * **CyberchefTool**: Generates instructions on how to use CyberChef for the specific task.
   * **OnlineSolverTool**: Generates instructions for using websites like dcode.fr for various ciphers.
   * **InteractiveTerminalTool**: Can be used for auxiliary commands like viewing decrypted files.

4. **Validate Plan**: The Crypto_Verifier agent reviews the complete plan (cipher identification and solution steps), checking if the identification is plausible and if the suggested tools/methods/instructions are correct for the identified cipher.

5. **Iterate**: If the Crypto_Verifier finds issues, it provides specific feedback (e.g., "Feedback: The text appears to be Base64 encoded before Vigenere encryption. Update the plan to use CryptoLibTool first, then suggest Vigenere steps."). The crew refines the plan within the ModuleAnalysisFlow.

6. **Output**: The final, validated decryption plan is saved as a markdown ticket.