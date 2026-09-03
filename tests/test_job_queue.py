import asyncio
import threading

import pytest

from dtos import PromptItem
from job_queue import GenerationQueue


def test_queue_runs_jobs_in_fifo_order():
    seen: list[str] = []

    def generate(prompt: PromptItem) -> str:
        seen.append(prompt.prompt_text)
        return f"done:{prompt.prompt_text}"

    async def scenario() -> None:
        queue = GenerationQueue(generate)
        queue.start_worker()
        try:
            first = await queue.enqueue(PromptItem(prompt_text="a", conversation_id=1))
            second = await queue.enqueue(PromptItem(prompt_text="b", conversation_id=1))
            assert await first.done == "done:a"
            assert await second.done == "done:b"
            assert seen == ["a", "b"]
            assert first.status == "done"
            assert second.status == "done"
        finally:
            await queue.stop_worker()

    asyncio.run(scenario())


def test_failed_generate_marks_job_failed():
    def generate(prompt: PromptItem) -> str:
        raise RuntimeError("boom")

    async def scenario() -> None:
        queue = GenerationQueue(generate)
        queue.start_worker()
        try:
            job = await queue.enqueue(PromptItem(prompt_text="x", conversation_id=1))
            with pytest.raises(RuntimeError, match="boom"):
                await job.done
            assert job.status == "failed"
            assert job.error == "boom"
        finally:
            await queue.stop_worker()

    asyncio.run(scenario())


def test_stop_worker_fails_queued_jobs():
    started = threading.Event()
    release = threading.Event()

    def generate(prompt: PromptItem) -> str:
        if prompt.prompt_text == "hold":
            started.set()
            release.wait(timeout=5)
        return "ok"

    async def scenario() -> None:
        queue = GenerationQueue(generate)
        queue.start_worker()
        hold = await queue.enqueue(PromptItem(prompt_text="hold", conversation_id=1))
        queued = await queue.enqueue(PromptItem(prompt_text="later", conversation_id=1))
        for _ in range(50):
            if started.is_set():
                break
            await asyncio.sleep(0.05)
        else:
            pytest.fail("in-flight generate never started")
        await queue.stop_worker()
        release.set()

        with pytest.raises(asyncio.CancelledError):
            await queued.done
        assert queued.status == "failed"
        try:
            await hold.done
        except asyncio.CancelledError:
            pass
        assert hold.status in {"running", "done", "failed"}

    asyncio.run(scenario())
