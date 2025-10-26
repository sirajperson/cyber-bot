import base64
import binascii
import logging
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai_tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class CryptoLibToolInput(BaseModel):
    """Input schema for CryptoLibTool."""
    mode: str = Field(..., description="The operation mode: 'encode' or 'decode'.")
    format: str = Field(..., description="The encoding format: 'base64' or 'hex'.")
    input_data: str = Field(..., description="The string data to encode or decode.")

class CryptoLibTool(BaseTool):
    name: str = "Python Encoding/Decoding"
    description: str = (
        "Uses Python libraries to encode or decode data using common formats like Base64 and Hexadecimal. "
        "Specify the mode ('encode'/'decode'), format ('base64'/'hex'), and the input data string."
    )
    args_schema: Type[BaseModel] = CryptoLibToolInput

    def _run(self, mode: str, format: str, input_data: str) -> str:
        """
        Performs encoding or decoding using Python libraries.
        """
        mode = mode.lower()
        format = format.lower()
        logger.info(f"Running Python crypto: mode='{mode}', format='{format}'")

        if mode not in ['encode', 'decode']:
            return "Error: Invalid mode. Use 'encode' or 'decode'."
        if format not in ['base64', 'hex']:
            return "Error: Invalid format. Use 'base64' or 'hex'."
        if not input_data:
             return "Error: Input data cannot be empty."

        try:
            if format == 'base64':
                if mode == 'encode':
                    # Assume input is UTF-8 string
                    input_bytes = input_data.encode('utf-8')
                    encoded_bytes = base64.b64encode(input_bytes)
                    result = encoded_bytes.decode('utf-8')
                    return f"Base64 Encoded: {result}"
                else: # decode
                    # Input is Base64 string
                    decoded_bytes = base64.b64decode(input_data)
                    # Try decoding as UTF-8, fallback to hex representation of bytes
                    try:
                         result = decoded_bytes.decode('utf-8')
                         return f"Base64 Decoded (UTF-8): {result}"
                    except UnicodeDecodeError:
                         result_hex = binascii.hexlify(decoded_bytes).decode('utf-8')
                         logger.warning("Base64 decoded data was not valid UTF-8, returning hex.")
                         return f"Base64 Decoded (Bytes as Hex): {result_hex}"

            elif format == 'hex':
                if mode == 'encode':
                    # Assume input is UTF-8 string
                    input_bytes = input_data.encode('utf-8')
                    encoded_hex = binascii.hexlify(input_bytes)
                    result = encoded_hex.decode('utf-8')
                    return f"Hex Encoded: {result}"
                else: # decode
                    # Input is Hex string
                    decoded_bytes = binascii.unhexlify(input_data)
                     # Try decoding as UTF-8, fallback to hex representation of bytes (less useful here)
                    try:
                         result = decoded_bytes.decode('utf-8')
                         return f"Hex Decoded (UTF-8): {result}"
                    except UnicodeDecodeError:
                         # For hex->bytes, just showing the bytes again isn't very helpful
                         # Maybe return raw byte representation?
                         logger.warning("Hex decoded data was not valid UTF-8.")
                         # Return raw bytes might confuse LLM, return error/note?
                         return f"Hex Decoded (Resulting bytes were not valid UTF-8)"


            # Should not reach here if format is validated
            return "Error: Unexpected format encountered."

        except binascii.Error as e:
            logger.error(f"Hex/Base64 processing error: {e}", exc_info=True)
            return f"Error during {format} {mode}: Invalid input data. Details: {e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred in CryptoLibTool: {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = CryptoLibTool()

    print("\n--- Test 1: Base64 Encode ---")
    result1 = tool.run(mode="encode", format="base64", input_data="Hello CrewAI!")
    print(result1) # Should be SGVsbG8gQ3Jld0FJIQ==

    print("\n--- Test 2: Base64 Decode ---")
    result2 = tool.run(mode="decode", format="base64", input_data="SGVsbG8gQ3Jld0FJIQ==")
    print(result2) # Should be Hello CrewAI!

    print("\n--- Test 3: Hex Encode ---")
    result3 = tool.run(mode="encode", format="hex", input_data="Secret")
    print(result3) # Should be 536563726574

    print("\n--- Test 4: Hex Decode ---")
    result4 = tool.run(mode="decode", format="hex", input_data="536563726574")
    print(result4) # Should be Secret

    print("\n--- Test 5: Invalid Base64 Decode ---")
    result5 = tool.run(mode="decode", format="base64", input_data="Not Valid Base64!!")
    print(result5)

    print("\n--- Test 6: Invalid Hex Decode ---")
    result6 = tool.run(mode="decode", format="hex", input_data="NotValidHexG")
    print(result6)
