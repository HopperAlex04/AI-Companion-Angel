from fastapi import FastAPI
from pydantic import BaseModel
from providers import MockProvider
import requests

app = FastAPI()

# client = OpenAI(
#     base_url="http://0.0.0.0:8080",
#     api_key="not-needed"
# )

class PromptItem(BaseModel):
    prompt_text: str

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/chat/mock")
async def chatMock(prompt: PromptItem):
    provider = MockProvider()
    return provider.generate(prompt.prompt_text)

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
    response = requests.post(
        "http://0.0.0.0:8080/v1/chat/completions",
        json={
            "model": "google/gemma-4-E4B-it-qat-q4_0-gguf:IT",
            "messages": [
                    {"role": "user", "content": prompt.prompt_text}
                ],
            "temperature": 0.7,
        }
    )
    return response.json()["choices"][0]["message"]["content"]
