from dataclasses import dataclass
from enum import Enum
import os
import asyncio
from typing import Optional, List, Dict, Any
import aiohttp
import json
import base64
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pathlib import Path
from io import BytesIO
import requests

from src.common.config import Config

# Configure logging
logging.basicConfig(filename='logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    OPENROUTER = "openrouter"

class ModelType(Enum):
    CHAT = "chat"
    VISION = "vision"

@dataclass
class ModelConfig:
    model: str = "qwen/qwen3-vl-235b-a22b-instruct"  # Qwen Vision Model
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_retries: int = 3
    timeout: int = 60
    provider: ModelProvider = ModelProvider.OPENROUTER

@dataclass
class ImageConfig:
    model: str = "qwen/qwen3-vl-235b-a22b-instruct"
    size: str = "1792x1024"
    quality: str = "standard"
    max_retries: int = 3
    provider: ModelProvider = ModelProvider.OPENROUTER

class AIError(Exception):
    pass

class RateLimiter:
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            self.calls = [t for t in self.calls if now - t < 60]
            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            self.calls.append(now)

class OpenRouterAPI:
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise AIError("No OpenRouter API key found. Set OPENROUTER_API_KEY in .env.")
        self.vision_limiter = RateLimiter(calls_per_minute=50)
        logger.info("OpenRouterAPI initialized with Qwen Vision Model")

    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode an image file to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(AIError)
    )
    async def convert_to_markdown(self, html: str, image_path: Optional[str] = None) -> str:
        """Convert HTML and optional image to markdown using Qwen3-VL Vision Model."""
        await self.vision_limiter.acquire()

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            messages = [
                {"role": "user", "content": [{"type": "text", "text": f"Convert this HTML to markdown. Describe and integrate any image visually: {html}"}]}
            ]

            if image_path:
                base64_image = self.encode_image_to_base64(image_path)
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "qwen/qwen3-vl-235b-a22b-instruct",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        raise AIError(f"OpenRouter request failed with status {response.status}")
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Markdown conversion error: {str(e)}")
            raise AIError(f"Failed to convert to markdown: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(AIError)
    )
    async def analyze_image_for_navigation(self, image_path: Optional[str] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
        """Analyze an image for navigation purposes (e.g., detect buttons, text, or landmarks)."""
        if not image_path and not image_url:
            raise AIError("Provide image_path or image_url")

        await self.vision_limiter.acquire()

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            messages = [
                {"role": "user", "content": [{"type": "text", "text": "Analyze this image for navigation purposes. Identify buttons, text, or landmarks that can guide navigation, and return a JSON object with 'elements' (list of detected items) and 'description' (summary)."}]}
            ]

            if image_path:
                base64_image = self.encode_image_to_base64(image_path)
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})
            elif image_url:
                messages[0]["content"].append({"type": "image_url", "image_url": {"url": image_url}})

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "qwen/qwen3-vl-235b-a22b-instruct",
                        "messages": messages,
                        "temperature": 0.5,
                        "max_tokens": 1000,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        raise AIError(f"OpenRouter request failed with status {response.status}")
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content) if isinstance(content, str) else content

        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            raise AIError(f"Failed to analyze image for navigation: {str(e)}")

if __name__ == "__main__":
    import asyncio
    async def main():
        api = OpenRouterAPI()
        html_sample = "<h1>Test</h1><p>Content</p>"
        markdown = await api.convert_to_markdown(html_sample)
        print("Markdown:", markdown)

        # Test image analysis
        image_path = "path/to/your/image.jpg"
        navigation_data = await api.analyze_image_for_navigation(image_path)
        print("Navigation Analysis:", navigation_data)
    asyncio.run(main())