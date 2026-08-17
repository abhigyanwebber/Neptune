"""Reference tool: echo.

Input:  {"text": "hello"}
Output: {"echo": "hello"}

Purpose (per task B-004): validate the end-to-end tool execution path
with a tool that has no side effects, no web access, no shell, no
sandbox requirement.
"""

from __future__ import annotations

from neptune.core.contracts.model_gateway import ToolDefinition
from neptune.core.contracts.tool_execution import ToolInputError


class EchoTool:
    name = "echo"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="Echoes back the given text. Reference tool for validating the tool execution boundary.",
            parameters_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )

    def execute(self, arguments: dict) -> dict:
        if "text" not in arguments:
            raise ToolInputError("missing required argument: text")
        text = arguments["text"]
        if not isinstance(text, str):
            raise ToolInputError(f"argument 'text' must be a string, got {type(text).__name__}")
        return {"echo": text}
