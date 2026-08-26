from fastapi import FastAPI
from fastapi.responses import FileResponse
from providers import MockProvider, LlamaCPPProvider
from dtos import PromptItem
import sqlite3

app = FastAPI()
mock = MockProvider()
conn = sqlite3.connect("chat.db")
llamacpp = LlamaCPPProvider(conn)

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.post("/chat/mock")
async def chatMock(prompt: PromptItem):
    provider = MockProvider()
    return provider.generate(prompt)

@app.post("/chat/angel")
async def chatAngel(prompt:PromptItem):
    #response is a string
    response = llamacpp.generate(prompt)
    return response

@app.get("/conversations")
async def get_conversations():
    # value is a list opf tuples conatining and int (id) a string (title) and a sqlite datetime value (created_at)
    return llamacpp.get_all_conversations()
