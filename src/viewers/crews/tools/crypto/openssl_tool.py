import subprocess
import os
import logging
import shlex
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# --- Input Schema ---
class OpensslToolInput(BaseModel):
    """Input schema for OpensslTool (Simplified for AES Decrypt)."""
    cipher: str = Field(..., description="The openssl cipher name (e.g., 'aes-256-cbc', 'aes-128-ecb'). Must be a valid openssl cipher string.")
    input_file_path: str = Field(..., description="Path to the input file containing ciphertext, relative to '/app/data'.")
    output_file_path: str = Field(..., description="Path to save the decrypted output file, relative to '/app/data'.")
    key_hex: Optional[str] = Field(None, description="The decryption key in hexadecimal format (e.g., '001122...FF'). Required unless using passphrase.")
    iv_hex: Optional[str] = Field(None, description="The initialization vector (IV) in hexadecimal format. Required for modes like CBC.")
    passphrase: Optional[str] = Field(None, description="A passphrase to derive the key/IV using a KDF (e.g., PBKDF2). Use either key/IV or passphrase.")
    no_padding: bool = Field(False, description="Set to True if padding should be disabled ('-nopad').")
    use_base64: bool = Field(False, description="Set to True if the input file is Base64 encoded ('-a' or '-A').")

class OpensslTool(BaseTool):
    name: str = "OpenSSL Decryptor"
    description: str = (
        "Uses the 'openssl enc' command to decrypt files encrypted with symmetric ciphers like AES. "
        "Specify the cipher type (e.g., 'aes-256-cbc'), input/output file paths (relative to '/app/data'), "
        "and either the key/IV in hex or a passphrase. Can handle Base64 encoded input and disable padding."
    )
    args_schema: Type[BaseModel] = OpensslToolInput

    def _run(self, cipher: str, input_file_path: str, output_file_path: str,
             key_hex: Optional[str] = None, iv_hex: Optional[str] = None,
             passphrase: Optional[str] = None, no_padding: bool = False, use_base64: bool = False) -> str:
        """
        Executes the openssl enc command for decryption.
        """
        # --- Validate Inputs ---
        if not (key_hex or passphrase):
             return "Error: Either 'key_hex' or 'passphrase' must be provided for decryption."
        if key_hex and passphrase:
             return "Error: Provide either 'key_hex'/'iv_hex' OR 'passphrase', not both."
        # Basic check for common IV requirement (can be expanded)
        if 'cbc' in cipher.lower() and not iv_hex and not passphrase:
              if key_hex: # Only enforce if key_hex is used without IV, as passphrase might derive IV
                   return f"Error: Cipher '{cipher}' typically requires an IV ('iv_hex') when using a direct key."

        # --- Security/Context Check ---
        base_dir = "/app/data"
        # Sanitize input path
        in_relative = os.path.normpath(os.path.join('/', input_file_path.lstrip('/'))).lstrip('/')
        target_in_file = os.path.abspath(os.path.join(base_dir, in_relative))
        # Sanitize output path
        out_relative = os.path.normpath(os.path.join('/', output_file_path.lstrip('/'))).lstrip('/')
        target_out_file = os.path.abspath(os.path.join(base_dir, out_relative))

        if not target_in_file.startswith(base_dir) or not target_out_file.startswith(base_dir):
            logger.warning(f"Attempted path traversal: in='{input_file_path}', out='{output_file_path}'")
            return f"Error: Invalid file paths. Input and output must be within the data directory."
        if not os.path.isfile(target_in_file):
             logger.error(f"Input file not found for openssl: '{target_in_file}'")
             return f"Error: Input file not found at '{target_in_file}'."
        if os.path.exists(target_out_file) and target_out_file == target_in_file:
             return f"Error: Input and output file paths cannot be the same ('{output_file_path}')."

        # --- Construct Command ---
        command = [
            "openssl", "enc",
            f"-{cipher}", # Cipher name prefixed with '-'
            "-d", # Decrypt flag
            "-in", target_in_file,
            "-out", target_out_file,
        ]

        if use_base64:
             command.append("-A") # Process multi-line base64

        if key_hex:
            command.extend(["-K", key_hex.upper()]) # Uppercase K for hex key, ensure hex is uppercase
            if iv_hex:
                command.extend(["-iv", iv_hex.upper()]) # Ensure IV hex is uppercase
        elif passphrase:
            # Using env var is slightly safer than direct command line arg
            # command.extend(["-pass", f"pass:{passphrase}"])
            env = os.environ.copy()
            env['OPENSSL_PASS'] = passphrase # Use an environment variable
        else:
             env = os.environ.copy() # Use current env if no passphrase

        if no_padding:
            command.append("-nopad")

        logger.info(f"Executing command (passphrase omitted): {' '.join(shlex.quote(c) for c in command)}")

        # --- Execute Command ---
        try:
            process_env = env if passphrase else None # Pass env only if passphrase used
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False, # Capture stderr on failure
                timeout=60,
                env=process_env # Pass environment if needed
            )

            # --- Process Output ---
            output = f"OpenSSL decryption attempt for '{input_file_path}' to '{output_file_path}':\n"
            if result.stderr:
                output += f"--- stderr ---\n{result.stderr.strip()}\n"
            else:
                 output += "--- stderr ---\n(No standard error output)\n"
            if result.stdout:
                 output += f"--- stdout ---\n{result.stdout.strip()}\n"

            output += f"Exit Code: {result.returncode}\n"

            if result.returncode == 0:
                 output += f"\nSuccess: Decrypted output saved to '/app/data/{out_relative}'. Use 'cat' via Interactive Terminal to view it."
                 logger.info(f"OpenSSL decryption successful for {target_in_file}")
            else:
                 logger.error(f"OpenSSL decryption failed for {target_in_file}. Exit: {result.returncode}. Stderr: {result.stderr.strip()}")
                 output += "\nError: Decryption failed. Check stderr output above (e.g., 'bad decrypt', key/IV length error, padding error)."
                 if os.path.exists(target_out_file):
                     try: os.remove(target_out_file)
                     except OSError: logger.warning(f"Could not remove partial output file {target_out_file}")

            max_len = 2000
            if len(output) > max_len: output = output[:max_len] + "\n... (output truncated)"
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"OpenSSL command timed out for file '{input_file_path}'.")
            return f"Error: OpenSSL command timed out on '{input_file_path}'."
        except FileNotFoundError:
            logger.error("'openssl' command not found. Is it installed?")
            return "Error: 'openssl' command not found."
        except Exception as e:
            logger.error(f"Error running OpenSSL on '{input_file_path}': {e}", exc_info=True)
            return f"An unexpected error occurred running OpenSSL: {e}"

# Example usage (requires openssl and dummy files)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = OpensslTool()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../../../..'))
    data_dir_abs = os.path.join(project_root, 'data')
    os.makedirs(data_dir_abs, exist_ok=True)

    plain_rel = "plaintext_openssl.txt"
    enc_rel = "encrypted_openssl.enc"
    dec_rel = "decrypted_openssl.txt"
    plain_abs = os.path.join(data_dir_abs, plain_rel)
    enc_abs = os.path.join(data_dir_abs, enc_rel)
    dec_abs = os.path.join(data_dir_abs, dec_rel)
    key = "000102030405060708090A0B0C0D0E0F" # 128 bit hex key (needs upper for openssl)
    iv = "101112131415161718191A1B1C1D1E1F"  # 128 bit hex IV (needs upper for openssl)
    passphrase_test = "secretpass"

    encrypt_success = False
    encrypt_pass_success = False
    try:
        with open(plain_abs, "w") as f: f.write("This is a secret message via openssl.\n")
        print(f"Created plaintext file: {plain_abs}")

        # Encrypt using openssl on host (requires openssl) - Key/IV method
        enc_cmd = ["openssl", "enc", "-aes-128-cbc", "-e", "-in", plain_abs, "-out", enc_abs, "-K", key, "-iv", iv]
        print(f"Encrypting using Key/IV: {' '.join(enc_cmd)}")
        subprocess.run(enc_cmd, check=True, capture_output=True)
        print(f"Created encrypted file (Key/IV): {enc_abs}")
        encrypt_success = True

        # Encrypt using passphrase method
        enc_pass_rel = "encrypted_openssl_pass.enc"
        enc_pass_abs = os.path.join(data_dir_abs, enc_pass_rel)
        enc_pass_cmd = ["openssl", "enc", "-aes-128-cbc", "-e", "-in", plain_abs, "-out", enc_pass_abs, "-pass", f"pass:{passphrase_test}", "-pbkdf2"] # Use pbkdf2
        print(f"Encrypting using Passphrase: {' '.join(c for c in enc_pass_cmd if 'pass:' not in c)}")
        subprocess.run(enc_pass_cmd, check=True, capture_output=True)
        print(f"Created encrypted file (Passphrase): {enc_pass_abs}")
        encrypt_pass_success = True


        if encrypt_success:
            print("\n--- Test 1: Successful Decryption (Key/IV) ---")
            result1 = tool.run(cipher="aes-128-cbc", input_file_path=enc_rel, output_file_path=dec_rel, key_hex=key, iv_hex=iv)
            print(result1)
            if os.path.exists(dec_abs):
                with open(dec_abs, "r") as f: print(f"Decrypted content: {f.read().strip()}")
            else: print("Decryption failed (Key/IV), output file not created.")

            print("\n--- Test 2: Decryption with wrong key ---")
            wrong_key = "F" * 32
            result2 = tool.run(cipher="aes-128-cbc", input_file_path=enc_rel, output_file_path=dec_rel, key_hex=wrong_key, iv_hex=iv)
            print(result2)

            print("\n--- Test 3: Missing IV ---")
            result3 = tool.run(cipher="aes-128-cbc", input_file_path=enc_rel, output_file_path=dec_rel, key_hex=key) # Missing iv_hex
            print(result3)

        if encrypt_pass_success:
             print("\n--- Test 4: Successful Decryption (Passphrase) ---")
             # Clean up previous output first
             if os.path.exists(dec_abs): os.remove(dec_abs)
             result4 = tool.run(cipher="aes-128-cbc", input_file_path=enc_pass_rel, output_file_path=dec_rel, passphrase=passphrase_test)
             print(result4)
             if os.path.exists(dec_abs):
                 with open(dec_abs, "r") as f: print(f"Decrypted content (Passphrase): {f.read().strip()}")
             else: print("Decryption failed (Passphrase), output file not created.")

             print("\n--- Test 5: Decryption with wrong passphrase ---")
             result5 = tool.run(cipher="aes-128-cbc", input_file_path=enc_pass_rel, output_file_path=dec_rel, passphrase="wrongpass")
             print(result5)


    except FileNotFoundError:
         print("\n--- Could not run openssl for test setup: 'openssl' not found on host. Skipping execution tests. ---")
    except Exception as e:
        print(f"\n--- Error during test setup: {e}. Skipping execution tests. ---")
    finally:
        # Clean up
        files_to_remove = [plain_abs, enc_abs, dec_abs, enc_pass_abs if 'enc_pass_abs' in locals() else None]
        for f in files_to_remove:
             if f and os.path.exists(f): os.remove(f)
        print("\nCleaned up test files.")

