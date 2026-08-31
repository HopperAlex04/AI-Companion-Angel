from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]

    def execute(self, arguments: dict[str, Any]) -> str: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def dispatch(self, name: str, arguments: dict[str, Any] | str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"
        parsed = arguments
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError:
                return f"Invalid JSON arguments for {name}: {arguments}"
        if not isinstance(parsed, dict):
            return f"Arguments for {name} must be an object"
        try:
            return tool.execute(parsed)
        except Exception as exc:
            return f"Tool {name} failed: {exc}"


class WebSearchTool:
    name = "web_search"
    description = (
        "Search the web for current information. Use when facts may be stale, "
        "unknown, or need citations. Do not use for casual conversation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 8)",
            },
        },
        "required": ["query"],
    }

    def execute(self, arguments: dict[str, Any]) -> str:
        query = str(arguments.get("query") or "").strip()
        if not query:
            return "web_search failed: query is required"

        max_results = arguments.get("max_results", 5)
        try:
            max_results = int(max_results)
        except (TypeError, ValueError):
            max_results = 5
        max_results = max(1, min(max_results, 8))

        try:
            results = DDGS().text(query, max_results=max_results) or []
        except Exception as exc:
            return f"web_search failed: {exc}"

        if not results:
            return f"No search results for: {query}"

        lines = []
        for i, item in enumerate(results, start=1):
            title = item.get("title") or "(no title)"
            href = item.get("href") or ""
            body = item.get("body") or ""
            lines.append(f"{i}. {title}\n   {href}\n   {body}")
        return "\n".join(lines)
