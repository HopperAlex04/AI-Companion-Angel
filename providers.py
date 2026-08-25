from typing import final, override
import requests
from sqlite3 import Connection
from dtos import PromptItem

# import os
# import json
# import requests

SYSTEM_PROMPT = '''You are Angel, AI companion and research assistant.
You are designed to aid the user in designing AI systems by searching documentation, finding bugs, providing analysis of planned features and proposing implementations when requested'''

class ModelProvider:
    def generate(self, prompt: PromptItem) -> str:
        raise NotImplementedError("Subclasses must implement this method")

class MockProvider(ModelProvider):
    @override
    def generate(self, prompt: PromptItem):
        return f"prompt recieved: {prompt.prompt_text}"

class LlamaCPPProvider(ModelProvider):
    def __init__(self, conn: Connection):
        self.conn = conn

    @override
    def generate(self, prompt: PromptItem) -> str:
        # self.conversation.append({"role": "user", "content": prompt.prompt_text})
        conversation = []
        if not self.conversation_exists(prompt.conversation_id):
            conversation.append({"role": "system", "content": SYSTEM_PROMPT})
            conversation.append({"role": "user", "content": prompt.prompt_text})
            # TODO: Set up title generation
            self.add_conversation(str(prompt.conversation_id))
            self.add_message(prompt.conversation_id, "system", SYSTEM_PROMPT)
            self.add_message(prompt.conversation_id, "user", prompt.prompt_text)
        else:
            conversation = self.convert_conv(self.retrieve_conversation(prompt.conversation_id))
            print(conversation)
            conversation.append({"role": "user", "content": prompt.prompt_text})
            self.add_message(prompt.conversation_id, "user", prompt.prompt_text)
        response = requests.post(
            "http://0.0.0.0:8080/v1/chat/completions",
            json={
                "model": "google/gemma-4-E4B-it-qat-q4_0-gguf:IT",
                "messages": conversation,
                "temperature": 0.7,
            }
        )
        assistant_message = response.json()["choices"][0]["message"]

        conversation.append({"role": "assistant", "content": assistant_message["content"]})
        self.add_message(prompt.conversation_id, "assistant", assistant_message["content"])
        return assistant_message["content"]

    def retrieve_conversation(self, conv_id: int) -> list[tuple[str, str]]:
        # Grabs all messages, sorted by id, that belong to a conversation
        rows = self.conn.execute("select role, content from messages where conversation_id = ? order by id", (conv_id,)).fetchall()
        return rows

    def add_message(self, conv_id: int, role: str, content: str) -> None:
        # Add a message to a specified conversation by adding an entry to the messages table
        self.conn.execute("INSERT INTO messages (role, content, conversation_id) values (?,?,?)", (role, content, conv_id,))
        self.conn.commit()

    def add_conversation(self, title: str) -> int:
        # Add new conversation, use default time
        cursor = self.conn.execute("INSERT INTO conversations (title) VALUES (?) RETURNING id", (title,))
        con_id = cursor.fetchone()[0]
        self.conn.commit()
        return con_id

    def conversation_exists(self, conv_id: int) -> bool:
        # Check if a conversation with the given ID exists
        row = self.conn.execute("SELECT 1 FROM conversations WHERE id = ? LIMIT 1", (conv_id,)).fetchone()
        return row is not None

    def convert_conv(self, raw_conv: list[tuple[str, str]]) -> list[dict[str, str]]:
        # conversations are a tuple when retrieved, break it into dict with field 2 (role) and 3 (content)
        conversation = []
        for item in raw_conv:
            conversation.append({"role": item[0], "content": item[1]})
        return conversation
