from fastapi import FastAPI
from fastapi.responses import FileResponse
from providers import MockProvider, LlamaCPPProvider
from dtos import PromptItem, ConversationCreate
from tools import ToolRegistry, WebSearchTool
from config import CONFIG_PATH, config
import requests
import sqlite3

app = FastAPI()
mock = MockProvider()
conn = sqlite3.connect(config["database_path"])
registry = ToolRegistry()
registry.register(WebSearchTool())
llamacpp = LlamaCPPProvider(conn, registry)

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/config.json")
async def get_config():
    return FileResponse(CONFIG_PATH)

@app.post("/chat/mock")
async def chatMock(prompt: PromptItem):
    provider = MockProvider()
    return provider.generate(prompt)

@app.post("/chat/angel")
async def chatAngel(prompt:PromptItem):
    #response is a string
    response = requests.post("http://localhost:8000/generate", json=prompt.model_dump())
    return response

@app.get("/conversations")
async def get_conversations():
    conversations = requests.get("http://localhost:8000/conversations")
    return conversations.json()

@app.post("/conversations")
async def new_conversation(payload: ConversationCreate):
    response = requests.post("http://localhost:8000/conversations", json=payload.model_dump())
    id = response.json()["id"]
    return id
