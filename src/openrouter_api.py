import requests
import os
from .config import Config

class OpenRouterAPI:
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"

    def convert_to_markdown(self, html, image=None):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "gpt-4o",  # or claude-3-5-sonnet
            "messages": [{"role": "user", "content": f"Convert this HTML to markdown:\n\n{html}"}]
        }
        if image:
            payload["images"] = [image]  # Adjust for image handling
        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
