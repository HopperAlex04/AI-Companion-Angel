from ollama import chat

# import os
# import json
# import requests

SYSTEM_PROMPT = '''You are Angel, AI companion and research assistant.
You are designed to aid the user in designing AI systems by searching documentation, finding bugs, providing analysis of planned features and proposing implementations when requested'''

class ModelProvider:
    def generate(self, prompt: str) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

class MockProvider(ModelProvider):
    def generate(self, prompt: str) -> dict:
        return {"response": f"prompt recieved: {prompt}"}

class OllamaLocalProvider:

    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.message_history =[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    def clear_history(self):
        self.message_history = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    def get_history(self) -> list:
        return self.message_history

    def generate(self, prompt: str) -> dict:
        self.message_history.append({
            "role": "user",
            "content": prompt
        })

        response = chat(
            model=self.model,
            messages=self.message_history,
            stream=False,
            options={"temperature": 0.2}
        )

        content = response["message"]["content"]
        self.message_history.append({
            "role": "assistant",
            "content": content
        })

        print(self.message_history)

        return content
