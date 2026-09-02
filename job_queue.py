"""In-process FIFO queue for llama.cpp generations.

This is a classic producer/consumer setup in one process (no Redis/Celery):

- Producers: FastAPI handlers. Each POST /generate creates a Job and puts it
  on the queue, then waits on that job's Future.
- Consumer: a single worker task. It takes jobs in arrival order and runs
  generate one at a time so llama.cpp and SQLite never overlap.

asyncio.Queue is FIFO: the first put() is the first get(). One worker means
at most one generation is running.

Jobs live only in memory. Restarting the chat service drops the queue.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from dtos import PromptItem

# queued  -> sitting in the line, not started
# running -> worker has this job; generate() is in flight
# done    -> generate() returned; Future has the text
# failed  -> generate() raised (or worker was cancelled); Future has the error
JobStatus = Literal["queued", "running", "done", "failed"]

# Blocking generate(prompt) -> assistant text. Called from a worker thread.
GenerateFn = Callable[[PromptItem], str]


@dataclass
class Job:
    """One unit of work: a prompt waiting to be (or being) generated.

    `done` is an asyncio.Future. The HTTP handler awaits it. The worker
    completes it with set_result (text) or set_exception (error). That is
    how the original request unblocks without polling.
    """

    id: str
    prompt: PromptItem
    status: JobStatus
    created_at: datetime
    done: asyncio.Future[str]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "conversation_id": self.prompt.conversation_id,
            "created_at": self.created_at.isoformat(),
            "error": self.error,
        }


class GenerationQueue:
    """Holds the FIFO line, job lookup, and the single worker loop."""

    def __init__(self, generate: GenerateFn) -> None:
        self._generate = generate
        # Unbounded FIFO. put/get are awaitable so they never block the loop.
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        # All jobs this process has seen, newest last (insertion-ordered dict).
        self._jobs: dict[str, Job] = {}
        self._current: Job | None = None
        self._worker_task: asyncio.Task[None] | None = None

    async def enqueue(self, prompt: PromptItem) -> Job:
        """Producer: create a job, append it to the line, return it.

        The caller typically `await job.done` so the HTTP response waits
        until this job has been processed, while still letting later
        requests join the queue.
        """
        loop = asyncio.get_running_loop()
        job = Job(
            id=str(uuid.uuid4()),
            prompt=prompt,
            status="queued",
            created_at=datetime.now(timezone.utc),
            # Bound to this event loop so the worker can complete it from
            # the same loop after to_thread returns.
            done=loop.create_future(),
        )
        self._jobs[job.id] = job
        await self._queue.put(job)
        return job

    def start_worker(self) -> None:
        """Start the single consumer. Call once from FastAPI lifespan."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(
                self._worker_loop(),
                name="generation-worker",
            )

    async def stop_worker(self) -> None:
        """Cancel the worker on shutdown so the process can exit cleanly."""
        if self._worker_task is None:
            return
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None
        # Unblock HTTP handlers still waiting on jobs that never started.
        for job in self._jobs.values():
            if job.status == "queued" and not job.done.done():
                job.status = "failed"
                job.error = "worker cancelled"
                job.done.set_exception(asyncio.CancelledError())

    def snapshot(self) -> dict[str, Any]:
        """Status for GET / and GET /jobs: current work plus the line."""
        jobs = list(self._jobs.values())
        queued = [job for job in jobs if job.status == "queued"]
        return {
            "current": self._current.to_dict() if self._current else None,
            "queued_count": len(queued),
            "jobs": [job.to_dict() for job in jobs],
        }

    async def _worker_loop(self) -> None:
        """Consumer: wait for a job, run it, repeat until cancelled.

        get() yields while the queue is empty, so the event loop can still
        accept HTTP requests and enqueue more jobs.
        """
        while True:
            job = await self._queue.get()
            try:
                await self._run_job(job)
            finally:
                # Pairs with put(); unused unless someone calls queue.join().
                self._queue.task_done()

    async def _run_job(self, job: Job) -> None:
        job.status = "running"
        self._current = job
        try:
            # generate() uses blocking requests.post. Running it on the event
            # loop would freeze FastAPI for the whole llama.cpp call, so new
            # prompts could not even join the queue. to_thread keeps the loop
            # free; one worker still means one generation at a time.
            result = await asyncio.to_thread(self._generate, job.prompt)
            job.status = "done"
            if not job.done.done():
                job.done.set_result(result)
        except asyncio.CancelledError:
            job.status = "failed"
            job.error = "worker cancelled"
            if not job.done.done():
                job.done.set_exception(asyncio.CancelledError())
            raise
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            if not job.done.done():
                job.done.set_exception(exc)
        finally:
            if self._current is job:
                self._current = None
