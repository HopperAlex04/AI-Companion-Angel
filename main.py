from fastapi import FastAPI
from fastapi.responses import FileResponse
from providers import MockProvider, LlamaCPPProvider
from dtos import PromptItem, ConversationCreate
from tools import ToolRegistry, WebSearchTool
from config import CONFIG_PATH, config
import requests
import sqlite3
import httpx

app = FastAPI()
mock = MockProvider()
client = httpx.AsyncClient(timeout=None)
chat_service_url = config["chat_service_url"]

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
    response = await client.post(f"{chat_service_url}/generate", json=prompt.model_dump())
    return response.json()

@app.get("/conversations")
async def get_conversations():
    conversations = await client.get(f"{chat_service_url}/conversations")
    return conversations.json()

@app.post("/conversations")
async def new_conversation(payload: ConversationCreate):
    response = await client.post(f"{chat_service_url}/conversations", json=payload.model_dump())
    id = response.json()["id"]
    return {"id": id}
