from fastapi import FastAPI
from fastapi.responses import FileResponse
from providers import MockProvider, LlamaCPPProvider
from dtos import PromptItem, ConversationCreate
from tools import ToolRegistry, WebSearchTool
from config import CONFIG_PATH, config
from request_log import RequestLog
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
    req = RequestLog("chat/mock", label="Chat Request")
    try:
        provider = MockProvider()
        result = provider.generate(prompt)
        req.complete(200)
        return result
    except Exception as e:
        req.fail(e)
        raise

@app.post("/chat/angel")
async def chatAngel(prompt:PromptItem):
    req = RequestLog("chat/angel", label="Chat Request")
    try: 
        response = await client.post(f"{chat_service_url}/generate", json=prompt.model_dump())
        req.complete(response.status_code)
        return response.json()
    except Exception as e:
        req.fail(e)

@app.get("/conversations")
async def get_conversations():
    req = RequestLog("conversations", label="Conversations Request")
    try:
        conversations = await client.get(f"{chat_service_url}/conversations")
        req.complete(conversations.status_code)
        return conversations.json()
    except Exception as e:
        req.fail(e)
        return {"error": str(e)}

@app.post("/conversations")
async def new_conversation(payload: ConversationCreate):
    req = RequestLog("conversations", label="Conversations Request")
    try:
        response = await client.post(f"{chat_service_url}/conversations", json=payload.model_dump())
        id = response.json()["id"]
        req.complete(response.status_code)
        return {"id": id}
    except Exception as e:
        req.fail(e)
        raise
