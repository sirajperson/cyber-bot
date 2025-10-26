import logging
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai_tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class CyberchefToolInput(BaseModel):
    """Input schema for CyberchefTool."""
    task_description: str = Field(..., description="Describe the cryptographic task to perform (e.g., 'Decode Base64', 'Decrypt Vigenere with key SECRET', 'Analyze AES ciphertext').")
    input_data_description: str = Field(..., description="Describe or provide a snippet of the input data (ciphertext, encoded text).")
    recipe_suggestion: Optional[str] = Field(None, description="Optional: Suggest a specific CyberChef recipe or sequence of operations.")

class CyberchefTool(BaseTool):
    name: str = "CyberChef Instructions"
    description: str = (
        "Provides instructions and a link for using CyberChef (The Cyber Swiss Army Knife - a web app for data manipulation) "
        "to perform various cryptographic operations like encoding/decoding, encryption/decryption, hashing, etc. "
        "Describe the task, the input data, and optionally suggest a recipe."
    )
    args_schema: Type[BaseModel] = CyberchefToolInput
    cyberchef_url: str = "https://gchq.github.io/CyberChef/"

    def _run(self, task_description: str, input_data_description: str, recipe_suggestion: Optional[str] = None) -> str:
        """
        Returns instructions for using CyberChef.
        """
        logger.info(f"Generating CyberChef instructions for task: {task_description}")

        instructions = f"""
        **Instructions for using CyberChef:** ({self.cyberchef_url})

        **Task:** {task_description}
        **Input Data Hint:** {input_data_description}

        **Steps:**
        1.  **Open CyberChef:** Navigate to {self.cyberchef_url} in a web browser. 
        2.  **Input Data:** Paste the relevant input data (ciphertext, encoded text, etc.) into the top-right 'Input' panel.
        3.  **Build Recipe:** Drag and drop operations from the 'Operations' list (left panel) into the middle 'Recipe' panel.
        4.  **Configure Operations:** Adjust parameters for each operation in the 'Recipe' panel (e.g., enter keys, select modes, specify formats).
        5.  **View Output:** The result will appear in the bottom-right 'Output' panel.

        **Suggested Recipe/Operations (based on task):**
        """

        if recipe_suggestion:
            instructions += f"* {recipe_suggestion}\n"
        else:
            # Provide general suggestions based on keywords
            task_lower = task_description.lower()
            if "base64" in task_lower and "decode" in task_lower:
                instructions += "* Try dragging 'From Base64' into the Recipe.\n"
            elif "base64" in task_lower and "encode" in task_lower:
                 instructions += "* Try dragging 'To Base64' into the Recipe.\n"
            elif "hex" in task_lower and "decode" in task_lower:
                 instructions += "* Try dragging 'From Hex' into the Recipe.\n"
            elif "rot13" in task_lower:
                 instructions += "* Try dragging 'ROT13' into the Recipe.\n"
            elif "caesar" in task_lower:
                 instructions += "* Try dragging 'Caesar Box Cipher' or 'ROT13' (if shift is 13) into the Recipe. Adjust the shift amount.\n"
            elif "vigenere" in task_lower and "decrypt" in task_lower:
                 instructions += "* Try dragging 'Vigenere Decode' into the Recipe. Input the key if known, or try the 'Analyze Key Length' operation first.\n"
            elif "aes" in task_lower and "decrypt" in task_lower:
                 instructions += "* Try dragging 'AES Decrypt' into the Recipe. You will need the Key, IV (if applicable), and Mode (e.g., CBC, ECB).\n"
            else:
                instructions += "* Search the 'Operations' list for relevant keywords (e.g., 'decrypt', 'decode', 'hash', 'xor').\n"

        instructions += "\n**Note:** Experiment with different operations and parameters in CyberChef. Direct execution is not available through this interface."

        return instructions.strip()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = CyberchefTool()
    print("--- Test 1: Base64 Decode ---")
    result1 = tool.run(task_description="Decode Base64 text", input_data_description="SGVsbG8gQ3Jld0FJ")
    print(result1)
    print("\n--- Test 2: Vigenere with suggestion ---")
    result2 = tool.run(task_description="Decrypt Vigenere", input_data_description="Lipps Asvph", recipe_suggestion="Use 'Vigenere Decode' with key 'SECRET'")
    print(result2)
