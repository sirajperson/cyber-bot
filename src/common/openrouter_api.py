from dataclasses import dataclass # Removed 'field'
from enum import Enum
import os
import asyncio
from typing import Optional, List, Dict, Any
import aiohttp
import json
import base64
# Removed unused: from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Assuming Config is in the same directory or adjust import path
from .config import Config # Use relative import within the same package

# Configure logging
# Ensure log directory exists or adjust path as needed
log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'logs', 'bot.log')
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logging.basicConfig(filename=log_file_path, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    OPENROUTER = "openrouter"

class AIError(Exception):
    pass

# --- Configuration Classes ---
@dataclass
class APIConfig:
    """Base configuration for API access."""
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: Optional[str] = None
    max_retries: int = 3 # Default retry count
    timeout: int = 60 # Default request timeout
    provider: ModelProvider = ModelProvider.OPENROUTER

@dataclass
class ChatModelConfig(APIConfig):
    """Configuration specific to Chat models."""
    model: str = "qwen/qwen3-235b-a22b:free" # Default Chat model
    temperature: float = 0.7

@dataclass
class VisionModelConfig(APIConfig):
    """Configuration specific to Vision models."""
    model: str = "qwen/qwen3-vl-235b-a22b-instruct" # Default Vision model
    temperature: float = 0.2 # Often lower for vision analysis
    max_tokens_vision: int = 4000 # Default max tokens for vision tasks
    max_tokens_gui: int = 500    # Default max tokens for GUI action tasks


class RateLimiter:
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()
        try:
             self.loop = asyncio.get_running_loop()
        except RuntimeError:
             self.loop = asyncio.new_event_loop()
             asyncio.set_event_loop(self.loop)

    async def acquire(self):
        async with self.lock:
            now = self.loop.time()
            self.calls = [t for t in self.calls if now - t < 60]
            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60.0 - (now - self.calls[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds.")
                    await asyncio.sleep(sleep_time)
            self.calls.append(self.loop.time())


class OpenRouterAPI:
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.error("No OpenRouter API key found. Set OPENROUTER_API_KEY in .env or Config.")
            raise AIError("No OpenRouter API key found.")

        self.chat_config = ChatModelConfig(api_key=self.api_key)
        self.vision_config = VisionModelConfig(api_key=self.api_key)
        self.api_limiter = RateLimiter(calls_per_minute=50)

        logger.info(f"OpenRouterAPI initialized. Base URL: {self.chat_config.base_url}")
        logger.info(f"Chat Model: {self.chat_config.model}, Vision Model: {self.vision_config.model}")

    # --- Marked as staticmethod ---
    @staticmethod
    def encode_image_to_base64(image_path: str) -> str:
        """Encode an image file to base64."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
             logger.error(f"Image file not found for encoding: {image_path}")
             raise AIError(f"Image file not found: {image_path}")
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}", exc_info=True)
            raise AIError(f"Error encoding image: {e}")

    # --- Internal Helper for Making API Calls ---
    async def _make_api_call(self, payload: Dict[str, Any], config: APIConfig) -> Dict[str, Any]:
        """Internal helper to make POST requests to OpenRouter with rate limiting."""
        await self.api_limiter.acquire()
        request_url = f"{config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost", # Example
            "X-Title": "CyberBot AI Call" # Example
        }

        log_payload = {k: v for k, v in payload.items()}
        if 'messages' in log_payload:
            log_payload['messages'] = [{
                'role': m.get('role'),
                'content': [(c if c.get('type')=='text' else {'type': 'image_url', 'image_url': '...base64_data...'}) for c in m.get('content', [])]
            } for m in log_payload['messages']]
        logger.debug(f"Sending API request to {request_url}. Payload: {json.dumps(log_payload)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                request_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=config.timeout)
            ) as response:
                response_text = await response.text()
                logger.debug(f"API Raw Response (Status {response.status}): {response_text[:500]}...")
                if response.status != 200:
                    raise AIError(f"OpenRouter request failed for model {payload.get('model')} with status {response.status}. Response: {response_text[:500]}")
                try:
                    result = json.loads(response_text)
                    return result
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON response: {response_text[:500]}")
                    raise AIError(f"Failed to decode JSON response from OpenRouter.")

    # --- Vision Model Methods ---
    @retry(
        # --- Fixed: Use default int value from APIConfig ---
        stop=stop_after_attempt(APIConfig.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AIError)
    )
    async def convert_to_markdown(self, html: str, image_path: Optional[str] = None) -> str:
        """Convert HTML and optional image to markdown using the configured Vision model."""
        logger.info(f"Converting HTML to Markdown (with image: {image_path is not None})...")
        try:
            messages = [{"role": "user", "content": [{"type": "text", "text": f"Convert the following HTML content to clean, well-structured Markdown. If an image is provided, analyze its content and describe it visually within the Markdown where appropriate:\n\nHTML:\n```html\n{html}\n```"}]}]
            if image_path:
                # --- Use static method ---
                base64_image = OpenRouterAPI.encode_image_to_base64(image_path)
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})

            payload = {
                "model": self.vision_config.model,
                "messages": messages,
                "temperature": self.vision_config.temperature,
                "max_tokens": self.vision_config.max_tokens_vision
            }
            result = await self._make_api_call(payload, self.vision_config)
            markdown_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not markdown_content:
                 logger.warning("VLM returned empty content for markdown conversion.")
                 return "<!-- VLM returned empty content -->"
            logger.info("Markdown conversion successful.")
            return markdown_content.strip()
        except AIError: raise
        except Exception as e:
            logger.error(f"Markdown conversion error: {e}", exc_info=True)
            raise AIError(f"Failed to convert to markdown: {e}")

    @retry(
        # --- Fixed: Use default int value from APIConfig ---
        stop=stop_after_attempt(APIConfig.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AIError)
    )
    async def analyze_image_for_navigation(self, image_path: Optional[str] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
        """Analyze an image for navigation purposes using the configured Vision model."""
        if not image_path and not image_url: raise AIError("Provide image_path or image_url for navigation analysis.")
        logger.info(f"Analyzing image for navigation (image_path: {image_path is not None}, image_url: {image_url is not None})...")
        try:
            messages = [{"role": "user", "content": [{"type": "text", "text": "Analyze the attached screenshot for web navigation..."}]}] # Shortened prompt text for brevity
            if image_path:
                # --- Use static method ---
                base64_image = OpenRouterAPI.encode_image_to_base64(image_path)
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})
            elif image_url:
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": image_url}})

            payload = {
                "model": self.vision_config.model,
                "messages": messages,
                "temperature": self.vision_config.temperature,
                "max_tokens": 1500,
                "response_format": {"type": "json_object"}
            }
            result = await self._make_api_call(payload, self.vision_config)
            content_str = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            try:
                nav_json = json.loads(content_str)
                if not isinstance(nav_json, dict): raise ValueError("Not a dict")
                logger.info("Navigation analysis successful.")
                return nav_json
            except (json.JSONDecodeError, ValueError) as json_err:
                logger.error(f"Failed to parse VLM navigation content as JSON object: {json_err}. Content: {content_str}")
                raise AIError(f"VLM response content could not be parsed as valid JSON: {content_str[:200]}...")
        except AIError: raise
        except Exception as e:
            logger.error(f"Navigation image analysis error: {e}", exc_info=True)
            raise AIError(f"Failed to analyze image for navigation: {e}")

    @retry(
        # --- Fixed: Use default int value from APIConfig ---
        stop=stop_after_attempt(APIConfig.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(AIError)
    )
    async def analyze_gui_action(self, image_path: str, instruction: str) -> Dict[str, Any]:
        """Analyzes screenshot/instruction for GUI action using the configured Vision model."""
        logger.info(f"Analyzing GUI action: '{instruction}' with screenshot: {image_path}")
        try:
             # --- Use static method ---
            base64_image = OpenRouterAPI.encode_image_to_base64(image_path)
            prompt_text = (f"Analyze the attached screenshot based on the instruction: '{instruction}'. Respond ONLY with a JSON object...") # Shortened prompt
            messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}]}]
            payload = {
                "model": self.vision_config.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": self.vision_config.max_tokens_gui,
                "response_format": {"type": "json_object"}
            }
            result = await self._make_api_call(payload, self.vision_config)
            content_str = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            try:
                action_json = json.loads(content_str)
                if not isinstance(action_json, dict): raise ValueError("Not a dict")
                logger.info("GUI action analysis successful.")
                return action_json
            except (json.JSONDecodeError, ValueError) as json_err:
                 logger.error(f"Failed to parse VLM content as JSON object: {json_err}. Content: {content_str}")
                 raise AIError(f"VLM response content could not be parsed as valid JSON action: {content_str[:200]}...")
        except AIError: raise
        except Exception as e:
            logger.error(f"Error during VLM GUI action analysis: {e}", exc_info=True)
            raise AIError(f"Failed to analyze GUI action: {e}")

    # --- Chat Model Method ---
    @retry(
        # --- Fixed: Use default int value from APIConfig ---
        stop=stop_after_attempt(APIConfig.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AIError)
    )
    async def chat_completion(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        """Performs a chat completion using the configured Chat model."""
        logger.info(f"Performing chat completion with {len(messages)} messages...")
        try:
            payload = {
                "model": self.chat_config.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.chat_config.temperature,
                "max_tokens": max_tokens if max_tokens is not None else 2000
            }
            result = await self._make_api_call(payload, self.chat_config)
            chat_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not chat_response: logger.warning("Chat model returned empty content.")
            logger.info("Chat completion successful.")
            return chat_response.strip()
        except AIError: raise
        except Exception as e:
            logger.error(f"Chat completion error: {e}", exc_info=True)
            raise AIError(f"Failed to get chat completion: {e}")

