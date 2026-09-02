from fastapi import FastAPI
from dtos import PromptItem, ConversationCreate
from tools import ToolRegistry, WebSearchTool
from providers import LlamaCPPProvider
import sqlite3
from config import config

app = FastAPI()
conn = sqlite3.connect(config["database_path"])
registry = ToolRegistry()
registry.register(WebSearchTool())
llamacpp = LlamaCPPProvider(conn, registry)

@app.get("/")
async def root():
    # Maybe it returns current job information?
    return {"message": "Hello World"}

@app.get("/generate")
async def generate(prompt: PromptItem):
    return llamacpp.generate(prompt)

@app.get("/conversations")
async def get_conversations():
    conversations = llamacpp.get_all_conversations()
    for conversation in conversations:
        print(conversation)
    return conversations

@app.post("/conversations")
async def new_conversation(payload: ConversationCreate):
    id = llamacpp.add_conversation(payload.title)
    return {"id": id}