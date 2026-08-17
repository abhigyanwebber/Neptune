"""Tool / Permission boundary contract.

Core Runtime orchestrates tool *requests* and consumes the resulting
*observation* -- it never executes shell/filesystem/git/browser/MCP/sandbox
operations itself (director brief: Core must depend on this abstraction
rather than directly executing tools; execution/permission/sandbox belongs
to Claude B's infrastructure lane).
"""
from __future__ import annotations

from typing import Any, Protocol


class ToolPort(Protocol):
    def execute(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        """Submit a tool request and return an observation.

        `tool_call` and the returned observation are opaque dicts from
        Core's point of view -- permission checks, sandboxing, and actual
        execution are entirely the responsibility of whatever implements
        this Protocol (Claude B's tool/permission/sandbox layer).
        """
        ...
