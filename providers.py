from typing import override
import requests

# import os
# import json
# import requests

SYSTEM_PROMPT = '''You are Angel, AI companion and research assistant.
You are designed to aid the user in designing AI systems by searching documentation, finding bugs, providing analysis of planned features and proposing implementations when requested'''

class ModelProvider:
    def generate(self, prompt: str):
        raise NotImplementedError("Subclasses must implement this method")

class MockProvider(ModelProvider):
    def generate(self, prompt: str):
        return {"response": f"prompt recieved: {prompt}"}

class LlamaCPPProvider(ModelProvider):
    @override
    def generate(self, prompt: str):
        response = requests.post(
            "http://0.0.0.0:8080/v1/chat/completions",
            json={
                "model": "google/gemma-4-E4B-it-qat-q4_0-gguf:IT",
                "messages": [
                        {"role": "user", "content": prompt}
                    ],
                "temperature": 0.7,
            }
        )

        return response.json()["choices"][0]["message"]["content"]
