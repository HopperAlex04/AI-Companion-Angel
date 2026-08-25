from typing import override
import requests
from sqlite3 import Connection
from main import PromptItem

# import os
# import json
# import requests

SYSTEM_PROMPT = '''You are Angel, AI companion and research assistant.
You are designed to aid the user in designing AI systems by searching documentation, finding bugs, providing analysis of planned features and proposing implementations when requested'''

class ModelProvider:
    def generate(self, prompt: PromptItem):
        raise NotImplementedError("Subclasses must implement this method")

class MockProvider(ModelProvider):
    def generate(self, prompt: PromptItem):
        return {"response": f"prompt recieved: {prompt.prompt_text}"}

class LlamaCPPProvider(ModelProvider):
    def __init__(self, conn: Connection):
        self.conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.conn = conn

    @override
    def generate(self, prompt: PromptItem):
        self.conversation.append({"role": "user", "content": prompt.prompt_text})
        response = requests.post(
            "http://0.0.0.0:8080/v1/chat/completions",
            json={
                "model": "google/gemma-4-E4B-it-qat-q4_0-gguf:IT",
                "messages": self.conversation,
                "temperature": 0.7,
            }
        )
        assistant_message = response.json()["choices"][0]["message"]

        self.conversation.append({"role": "assistant", "content": assistant_message["content"]})

        return assistant_message["content"]

    def retrieve_conversation(self, conv_id: int):
        # Grabs all messages, sorted by id, that belong to a conversation
        rows = self.conn.execute("select role, content from messages where conv_id = ? order by id", (conv_id,)).fetchall()
        return rows

    def add_message(self, conv_id:int, role:str, content:str):
        # Add a meesage to a specified converstaion by adding an entry to the messages table
        self.conn.execute("INSERT INTO messages (role, content, conv_id) values (?,?,?)", (role, content, conv_id,))

    def add_conversation(self, title:str):
        # Add new conversation, use default time
        cursor = self.conn.execute("INSERT INTO conversations (title) VALUES (?) RETURNING id", (title,))
        return cursor.fetchone()[0]

    def conversation_exists(self, conv_id: int) -> bool:
        # Check if a conversation with the given ID exists
        row = self.conn.execute("SELECT 1 FROM conversations WHERE id = ? LIMIT 1", (conv_id,)).fetchone()
        return row is not None
