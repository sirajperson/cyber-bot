import logging
from typing import Type, Any
from pydantic import BaseModel, Field
from crewai_tools import BaseTool
from collections import Counter
import string

logger = logging.getLogger(__name__)

# --- Input Schema ---
class FrequencyAnalysisToolInput(BaseModel):
    """Input schema for FrequencyAnalysisTool."""
    text: str = Field(..., description="The text (ciphertext) to analyze.")
    ignore_case: bool = Field(True, description="Whether to ignore case (treat 'a' and 'A' as the same).")
    only_letters: bool = Field(True, description="Whether to only count alphabetic characters.")

class FrequencyAnalysisTool(BaseTool):
    name: str = "Character Frequency Analysis"
    description: str = (
        "Calculates the frequency of each character in a given text. "
        "Useful for analyzing ciphertext to help identify classical substitution ciphers "
        "(like Caesar, Vigenere) by comparing frequencies to standard English letter frequencies."
    )
    args_schema: Type[BaseModel] = FrequencyAnalysisToolInput

    def _run(self, text: str, ignore_case: bool = True, only_letters: bool = True) -> str:
        """
        Performs frequency analysis on the input text.
        """
        if not text:
            return "Error: Input text cannot be empty."

        logger.info(f"Performing frequency analysis (ignore_case={ignore_case}, only_letters={only_letters})...")

        processed_text = text
        if ignore_case:
            processed_text = processed_text.lower()

        if only_letters:
            processed_text = ''.join(filter(str.isalpha, processed_text))

        if not processed_text:
             return "Error: No characters left to analyze after filtering (check input and 'only_letters' flag)."

        # Calculate frequencies
        counts = Counter(processed_text)
        total_chars = len(processed_text)
        frequencies = {char: count / total_chars for char, count in counts.items()}

        # Sort by frequency (most common first)
        sorted_freq = sorted(frequencies.items(), key=lambda item: item[1], reverse=True)

        # Format output
        output = f"Frequency Analysis Results (Total relevant chars: {total_chars}):\n"
        output += "Char | Count | Frequency (%)\n"
        output += "-------------------------\n"
        for char, freq in sorted_freq:
            count = counts[char]
            output += f"  {char}  |  {count:<4} |  {freq * 100:.2f}%\n"

        # Add standard English frequencies for comparison if only_letters and ignore_case
        if only_letters and ignore_case:
             # Approximate frequencies
             english_freq = {
                 'e': 12.70, 't': 9.06, 'a': 8.17, 'o': 7.51, 'i': 6.97, 'n': 6.75,
                 's': 6.33, 'h': 6.09, 'r': 5.99, 'd': 4.25, 'l': 4.03, 'c': 2.78,
                 'u': 2.76, 'm': 2.41, 'w': 2.36, 'f': 2.23, 'g': 2.02, 'y': 1.97,
                 'p': 1.93, 'b': 1.29, 'v': 0.98, 'k': 0.77, 'j': 0.15, 'x': 0.15,
                 'q': 0.10, 'z': 0.07
             }
             output += "\nStandard English Letter Frequencies (%):\n"
             output += ", ".join([f"{k}: {v:.2f}" for k, v in english_freq.items()]) + "\n"


        logger.info("Frequency analysis complete.")
        return output.strip()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = FrequencyAnalysisTool()
    test_text = "Ebiil, Tloia! This is a simple test text for frequency analysis. E is the most common letter."
    print(f"--- Analyzing: '{test_text}' ---")
    result = tool.run(text=test_text)
    print(result)
    print("\n--- Analyzing (case-sensitive, all chars) ---")
    result_cs_all = tool.run(text=test_text, ignore_case=False, only_letters=False)
    print(result_cs_all)
