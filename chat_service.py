from contextlib import asynccontextmanager
import os
import sqlite3

from fastapi import FastAPI
from dtos import PromptItem, ConversationCreate
from tools import ToolRegistry, WebSearchTool
from providers import LlamaCPPProvider, ChatFn
from job_queue import GenerationQueue
from config import config


def create_app(
    conn: sqlite3.Connection,
    *,
    registry: ToolRegistry | None = None,
    chat_fn: ChatFn | None = None,
) -> FastAPI:
    """Build the chat service with an injected DB connection and optional mock LLM."""
    if registry is None:
        registry = ToolRegistry()
        registry.register(WebSearchTool())

    llamacpp = LlamaCPPProvider(conn, registry, chat_fn=chat_fn)
    generation_queue = GenerationQueue(llamacpp.generate)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        generation_queue.start_worker()
        yield
        await generation_queue.stop_worker()

    app = FastAPI(lifespan=lifespan)
    app.state.conn = conn
    app.state.provider = llamacpp
    app.state.generation_queue = generation_queue

    @app.get("/")
    async def root():
        return generation_queue.snapshot()

    @app.get("/jobs")
    async def list_jobs():
        return generation_queue.snapshot()["jobs"]

    @app.post("/generate")
    async def generate(prompt: PromptItem):
        job = await generation_queue.enqueue(prompt)
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

    return app


def create_production_app() -> FastAPI:
    # check_same_thread=False: generate() runs in a worker thread via
    # asyncio.to_thread, so SQLite would otherwise refuse this connection.
    # Safe here because the queue runs only one generation at a time, so two
    # threads never use `conn` concurrently.
    conn = sqlite3.connect(config["database_path"], check_same_thread=False)
    return create_app(conn)


# Skip the on-disk database when pytest sets ANGEL_TESTING before import.
if os.environ.get("ANGEL_TESTING") != "1":
    app = create_production_app()
