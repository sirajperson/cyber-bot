import logging
from typing import Type, Any, Optional, List
from pydantic import BaseModel, Field
from crewai_tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class OnlineSolverToolInput(BaseModel):
    """Input schema for OnlineSolverTool."""
    cipher_type: str = Field(..., description="The suspected type of cipher or encoding (e.g., 'Vigenere', 'Caesar', 'Morse Code', 'Baconian').")
    input_data_description: str = Field(..., description="Describe or provide a snippet of the input data (ciphertext, encoded text).")
    known_parameters: Optional[str] = Field(None, description="Any known parameters like a key, shift amount, or alphabet.")

class OnlineSolverTool(BaseTool):
    name: str = "Online Crypto Solver Instructions"
    description: str = (
        "Suggests useful online cryptography solver websites (like dcode.fr, Boxentriq, Cryptii) "
        "for various classical ciphers, encodings, and analysis techniques. "
        "Specify the suspected cipher type and provide a description or snippet of the data."
    )
    args_schema: Type[BaseModel] = OnlineSolverToolInput

    def _run(self, cipher_type: str, input_data_description: str, known_parameters: Optional[str] = None) -> str:
        """
        Returns links and instructions for using online crypto solvers.
        """
        logger.info(f"Generating online solver instructions for cipher: {cipher_type}")

        # Common useful solver sites
        solvers = {
            "dcode.fr": "https://www.dcode.fr/en (Comprehensive collection of many ciphers and tools)",
            "Boxentriq": "https://www.boxentriq.com/code-breaking (Focus on classical ciphers)",
            "Cryptii": "https://cryptii.com/ (Modular encoding/decoding/encryption)"
        }

        instructions = f"""
        **Instructions for using Online Crypto Solvers for '{cipher_type}':**

        **Input Data Hint:** {input_data_description}
        **Known Parameters:** {known_parameters or 'None'}

        **Recommended Online Tools:**
        * **dcode.fr:** {solvers['dcode.fr']} - Often has auto-detection features. Try searching for '{cipher_type}' on their site.
        * **Boxentriq:** {solvers['Boxentriq']} - Good for classical ciphers. Look for a '{cipher_type}' solver.
        * **Cryptii:** {solvers['Cryptii']} - Allows building pipelines for multi-stage encoding/decoding.

        **General Steps:**
        1.  **Visit Solver Site:** Navigate to one of the recommended sites (dcode.fr is often a good starting point).
        2.  **Find the Tool:** Locate the specific solver or analyzer for '{cipher_type}'. Use the site's search function if needed.
        3.  **Input Data:** Paste the ciphertext or encoded data into the appropriate input field.
        4.  **Provide Parameters:** If you know parameters (like a key for Vigenere, a shift for Caesar), enter them into the designated fields.
        5.  **Execute:** Click the 'Decrypt', 'Decode', 'Solve', or 'Analyze' button.
        6.  **Examine Output:** Check the results for meaningful plaintext or the flag. If unsuccessful, try different parameters or a different solver.

        **Note:** Direct interaction with these websites is not available. Use a web browser to access them and follow these steps as part of your analysis plan.
        """

        return instructions.strip()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = OnlineSolverTool()
    print("--- Test 1: Vigenere ---")
    result1 = tool.run(cipher_type="Vigenere", input_data_description="Lipps Asvph", known_parameters="Key might be 'SECRET'")
    print(result1)
    print("\n--- Test 2: Base64 ---")
    result2 = tool.run(cipher_type="Base64", input_data_description="SGVsbG8gQ3Jld0FJ")
    print(result2)
