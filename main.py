from fastapi import FastAPI
from providers import MockProvider, LlamaCPPProvider
from dtos import PromptItem
import sqlite3

app = FastAPI()
mock = MockProvider()
conn = sqlite3.connect("chat.db")
llamacpp = LlamaCPPProvider(conn)
# client = OpenAI(
#     base_url="http://0.0.0.0:8080",
#     api_key="not-needed"
# )

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/chat/mock")
async def chatMock(prompt: PromptItem):
    provider = MockProvider()
    return provider.generate(prompt)

@app.post("/chat/angel")
async def chatAngel(prompt:PromptItem):
    # response = client.chat.completions.create(
    #     model="google/gemma-4-E4B-it-qat-q4_0-gguf:IT",
    #     messages=[
    #         {"role": "user", "content": prompt.prompt_text}
    #     ],
    #     temperature=0.7,
    #     max_tokens=256
    # )
    #
    response = llamacpp.generate(prompt)
    return response
