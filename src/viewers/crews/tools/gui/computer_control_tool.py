import logging
import os
import time
import asyncio
from typing import Type, Optional, Dict, Any
import json

import mss
import mss.tools
import pyautogui
from pydantic import BaseModel, Field

from crewai.tools import BaseTool

# Assuming OpenRouterAPI is updated with a method for GUI analysis
from .....common.openrouter_api import OpenRouterAPI, AIError # Adjust relative path if needed

logger = logging.getLogger(__name__)

# --- Pydantic Input Schema ---
class ComputerControlToolInput(BaseModel):
    """Input schema for the ComputerControlTool."""
    instruction: str = Field(..., description="The natural language instruction for the GUI action (e.g., 'Click the File menu', 'Type Hello World into the search bar').")
    screenshot_path: Optional[str] = Field(None, description="Optional path to save the screenshot taken before executing the instruction. Defaults to a temporary path if not provided.")

# --- Tool Definition ---
class ComputerControlTool(BaseTool):
    name: str = "GUI Computer Control"
    description: str = (
        "Takes a natural language instruction and executes it on the computer's graphical user interface (GUI). "
        "It captures the screen, sends the instruction and screenshot to a Vision-Language Model (VLM) "
        "to determine the action (e.g., CLICK, TYPE, SCROLL) and parameters (coordinates, text), "
        "and then performs the action using mouse and keyboard control. "
        "⚠️ USE WITH EXTREME CAUTION: This tool directly controls the mouse and keyboard."
    )
    args_schema: Type[BaseModel] = ComputerControlToolInput
    openrouter_api: OpenRouterAPI = None # Instance will be created in __init__

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize the API client when the tool is created
        try:
            self.openrouter_api = OpenRouterAPI()
            logger.info("ComputerControlTool initialized with OpenRouterAPI.")
        except AIError as e:
            logger.error(f"Failed to initialize OpenRouterAPI for ComputerControlTool: {e}")
            self.openrouter_api = None # Ensure it's None if init fails

    def _take_screenshot(self, output_path: str) -> bool:
        """Takes a screenshot of the primary monitor using mss."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] # [0] is all monitors, [1] is primary
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_path)
            logger.info(f"Screenshot saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}", exc_info=True)
            return False

    def _execute_gui_action(self, action_data: Dict[str, Any]) -> str:
        """Parses VLM response and executes action using pyautogui."""
        action_type = action_data.get("action", "").upper()
        
        try:
            if action_type == "CLICK":
                x = int(action_data.get("x", 0))
                y = int(action_data.get("y", 0))
                logger.info(f"Executing CLICK at ({x}, {y})")
                pyautogui.click(x=x, y=y)
                time.sleep(0.5) # Small pause after action
                return f"Successfully clicked at coordinates ({x}, {y})."

            elif action_type == "TYPE":
                text_to_type = action_data.get("text", "")
                interval = action_data.get("interval", 0.05) # Delay between keystrokes
                logger.info(f"Executing TYPE: '{text_to_type}'")
                pyautogui.typewrite(text_to_type, interval=interval)
                time.sleep(0.5)
                return f"Successfully typed: '{text_to_type}'."
            
            elif action_type == "SCROLL":
                amount = int(action_data.get("amount", 0)) # Positive for up, negative for down
                direction = action_data.get("direction", "down").lower()
                if direction == "down":
                    amount = -abs(amount)
                else: # Assume up
                     amount = abs(amount)
                logger.info(f"Executing SCROLL: {amount} units")
                pyautogui.scroll(amount)
                time.sleep(0.5)
                return f"Successfully scrolled {amount} units."

            # Add other actions like DOUBLE_CLICK, KEY_PRESS, DRAG etc. as needed
            # elif action_type == "KEY_PRESS":
            #    key = action_data.get("key")
            #    pyautogui.press(key) ... etc.

            else:
                logger.warning(f"Unsupported action type received from VLM: {action_type}")
                return f"Error: Unsupported action type '{action_type}' received from VLM."

        except Exception as e:
            logger.error(f"Error executing GUI action '{action_type}': {e}", exc_info=True)
            return f"Error executing GUI action '{action_type}': {e}"


    def _run(self, instruction: str, screenshot_path: Optional[str] = None) -> str:
        """Captures screen, gets VLM analysis, and executes GUI action."""
        if not self.openrouter_api:
             return "Error: OpenRouterAPI client failed to initialize for ComputerControlTool."

        temp_screenshot_path = screenshot_path or "/tmp/crewai_gui_screenshot.png" # Use /tmp for temporary files

        # 1. Take Screenshot
        if not self._take_screenshot(temp_screenshot_path):
            return "Error: Failed to capture screenshot."

        # 2. Call VLM via OpenRouterAPI for action analysis
        try:
            logger.info("Calling VLM to analyze GUI instruction...")
            # --- We need to add a method like this to OpenRouterAPI ---
            # It should take image_path and instruction, and return JSON
            action_response_json = asyncio.run(
                self.openrouter_api.analyze_gui_action(
                    image_path=temp_screenshot_path,
                    instruction=instruction
                )
            )
            # --- End of required new OpenRouterAPI method ---

            if not isinstance(action_response_json, dict):
                 try:
                      # Sometimes VLM might return JSON as a string
                      action_data = json.loads(str(action_response_json))
                 except json.JSONDecodeError:
                      logger.error(f"VLM response was not valid JSON: {action_response_json}")
                      return f"Error: VLM response was not valid JSON: {str(action_response_json)[:200]}..."
            else:
                 action_data = action_response_json

            logger.info(f"VLM proposed action: {action_data}")

        except AIError as e:
            logger.error(f"VLM analysis failed: {e}", exc_info=True)
            return f"Error: VLM failed to analyze the instruction and screenshot: {e}"
        except Exception as e:
             logger.error(f"Unexpected error during VLM call: {e}", exc_info=True)
             return f"Error during VLM analysis: {e}"
        finally:
            # Clean up temporary screenshot if default path was used
             if not screenshot_path and os.path.exists(temp_screenshot_path):
                 try:
                     os.remove(temp_screenshot_path)
                 except OSError as e:
                     logger.warning(f"Could not remove temporary screenshot {temp_screenshot_path}: {e}")


        # 3. Execute the action determined by VLM
        if not action_data:
             return "Error: VLM did not return actionable data."
             
        execution_result = self._execute_gui_action(action_data)
        return execution_result

# Example usage (for local testing - WILL CONTROL YOUR MOUSE/KEYBOARD)
if __name__ == "__main__":
    print("--- ⚠️ Testing ComputerControlTool ---")
    print("--- ⚠️ THIS WILL TAKE SCREENSHOTS AND ATTEMPT TO CONTROL YOUR MOUSE/KEYBOARD ---")
    print("--- Make sure OpenRouterAPI is configured and Qwen3-VL model is accessible ---")
    print("--- Have a simple text editor open and visible for the 'TYPE' test ---")
    print("--- Starting in 5 seconds... Press Ctrl+C to cancel ---")
    time.sleep(5)

    control_tool = ComputerControlTool()

    # --- Test Case 1: Simple Click (Coordinates will depend on VLM and your screen) ---
    # instruction1 = "Click on the top-left corner of the screen"
    # print(f"\n--- Test 1: {instruction1} ---")
    # result1 = control_tool.run(instruction=instruction1)
    # print(result1)
    # time.sleep(2)

    # --- Test Case 2: Typing ---
    # !! ENSURE A TEXT EDITOR IS ACTIVE AND VISIBLE BEFORE RUNNING !!
    instruction2 = "Find a text input field or editor and type 'Hello World from CrewAI!'"
    print(f"\n--- Test 2: {instruction2} ---")
    print("Ensure a text editor is focused...")
    time.sleep(3) # Give user time to focus editor
    result2 = control_tool.run(instruction=instruction2)
    print(result2)
    time.sleep(2)

    # --- Test Case 3: Scrolling ---
    instruction3 = "Scroll down a little bit"
    print(f"\n--- Test 3: {instruction3} ---")
    result3 = control_tool.run(instruction=instruction3)
    print(result3)
    time.sleep(2)

    print("\n--- Testing Complete ---")

