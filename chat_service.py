from contextlib import asynccontextmanager

from fastapi import FastAPI
from dtos import PromptItem, ConversationCreate
from tools import ToolRegistry, WebSearchTool
from providers import LlamaCPPProvider
from job_queue import GenerationQueue
import sqlite3
from config import config

# check_same_thread=False: generate() runs in a worker thread via
# asyncio.to_thread, so SQLite would otherwise refuse this connection.
# Safe here because the queue runs only one generation at a time, so two
# threads never use `conn` concurrently.
conn = sqlite3.connect(config["database_path"], check_same_thread=False)
registry = ToolRegistry()
registry.register(WebSearchTool())
llamacpp = LlamaCPPProvider(conn, registry)
generation_queue = GenerationQueue(llamacpp.generate)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: one worker for the life of the process.
    generation_queue.start_worker()
    yield
    # Shutdown: stop taking new work so uvicorn can exit.
    await generation_queue.stop_worker()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return generation_queue.snapshot()


@app.get("/jobs")
async def list_jobs():
    return generation_queue.snapshot()["jobs"]


@app.post("/generate")
async def generate(prompt: PromptItem):
    job = await generation_queue.enqueue(prompt)
    # Same HTTP contract as before: wait until this prompt is generated,
    # even if other jobs are ahead in the FIFO line.
    return await job.done


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
