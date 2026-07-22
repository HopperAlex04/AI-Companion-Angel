from fastapi import FastAPI
from pydantic import BaseModel
from providers import MockProvider, OllamaLocalProvider

app = FastAPI()
ollama_p = OllamaLocalProvider()

class PromptItem(BaseModel):
    prompt_text: str

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/chat/mock")
async def chatMock(prompt: PromptItem):
    provider = MockProvider()

    return provider.generate(prompt.prompt_text)

@app.post("/chat")
async def chatLocal(prompt: PromptItem):
    return ollama_p.generate(prompt.prompt_text)

@app.get("/chat/clear")
async def clearLocalChat():
    return ollama_p.clear_history()
