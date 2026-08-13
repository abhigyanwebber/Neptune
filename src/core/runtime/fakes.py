"""Reference/test-double implementations of the Model Gateway and Tool
boundary Protocols.

These are NOT production code and must never be used as a real Gateway or
Tool layer -- they exist so Core Runtime is fully testable and demoable
without Claude B's real implementations (director brief). They are simple,
deterministic, and scripted rather than "smart" in any way.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


class FakeModelGateway:
    """Returns scripted responses in order, or a default response if the
    script is exhausted. `default_response_fn` lets tests express simple
    policies (e.g. "call one tool then stop") without a real model."""

    def __init__(
        self,
        scripted_responses: Optional[list[dict[str, Any]]] = None,
        default_response_fn: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    ) -> None:
        self._script = list(scripted_responses or [])
        self._default_response_fn = default_response_fn
        self.requests_received: list[dict[str, Any]] = []

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests_received.append(request)
        if self._script:
            return self._script.pop(0)
        if self._default_response_fn is not None:
            return self._default_response_fn(request)
        return {"content": "ok", "tool_calls": []}


class FakeToolPort:
    """Echoes back a deterministic observation for any tool call. Suitable
    for exercising the tool-request/observation lifecycle without any real
    execution (no shell, no filesystem, no sandbox)."""

    def __init__(self) -> None:
        self.calls_received: list[dict[str, Any]] = []

    def execute(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        self.calls_received.append(tool_call)
        return {
            "tool_name": tool_call.get("tool_name", "unknown"),
            "status": "ok",
            "result": f"fake-observation-for-{tool_call.get('tool_name', 'unknown')}",
        }
