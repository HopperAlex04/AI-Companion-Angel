from ollama import chat

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
