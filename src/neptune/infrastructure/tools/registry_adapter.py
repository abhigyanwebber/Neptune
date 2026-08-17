"""In-memory tool registry.

Simplest possible implementation of the ToolRegistry Protocol --
registration is explicit and in-process. No discovery, no MCP, no
dynamic loading (all explicitly out of scope for B-004).
"""

from __future__ import annotations

from neptune.core.contracts.model_gateway import ToolDefinition
from neptune.core.contracts.tool_execution import Tool, ToolNotFoundError


class ToolRegistryAdapter:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(name) from None

    def list_tools(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]
