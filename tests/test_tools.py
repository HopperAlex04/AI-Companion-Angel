from tests.fakes import FakeTool
from tools import ToolRegistry


def test_dispatch_unknown_tool():
    registry = ToolRegistry()
    assert registry.dispatch("missing", {"query": "x"}) == "Unknown tool: missing"


def test_dispatch_invalid_json():
    registry = ToolRegistry()
    registry.register(FakeTool())
    result = registry.dispatch("web_search", "{not-json")
    assert result.startswith("Invalid JSON arguments for web_search")


def test_dispatch_executes_registered_tool():
    tool = FakeTool(result="ok")
    registry = ToolRegistry()
    registry.register(tool)
    assert registry.dispatch("web_search", '{"query": "abc"}') == "ok"
    assert tool.calls == [{"query": "abc"}]


def test_openai_tools_shape():
    registry = ToolRegistry()
    registry.register(FakeTool())
    spec = registry.openai_tools()
    assert spec[0]["type"] == "function"
    assert spec[0]["function"]["name"] == "web_search"
