class ScriptedChat:
    """Stand-in for llama.cpp: returns queued OpenAI-style assistant messages."""

    def __init__(self, responses: list[dict] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[list[dict]] = []

    def __call__(self, messages: list[dict]) -> dict:
        self.calls.append([dict(message) for message in messages])
        if not self.responses:
            raise AssertionError("ScriptedChat received more _chat calls than responses")
        return self.responses.pop(0)


class FakeTool:
    name = "web_search"
    description = "Fake search used in tests"
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self, result: str = "fake search results") -> None:
        self.result = result
        self.calls: list[dict] = []

    def execute(self, arguments: dict) -> str:
        self.calls.append(arguments)
        return self.result
