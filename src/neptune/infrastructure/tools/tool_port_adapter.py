"""Adapter satisfying Claude A's core.contracts.tools.ToolPort Protocol
by wrapping Neptune's own ToolExecutor (B-004 / TOOL_CONTRACT).

core.contracts.tools.ToolPort.execute(tool_call: dict) -> dict is
deliberately opaque from Core's point of view and carries no
task/session/turn attribution -- Core Runtime's own tool_call dict is
just {"tool_name": ..., "args": ...}. Neptune's ToolCall (frozen
TOOL_CONTRACT shape) requires that attribution per its own invariant 2
("external side effects are attributable to a task/session/agent").

This adapter is the seam: it supplies the attribution context at
construction time (bound once per Runtime instance / process) so
Core's opaque calls still produce properly-attributed ToolResults on
Neptune's side, without requiring any change to core.contracts.tools
or core.runtime.engine/driver (B-006 explicitly forbids redesigning
either). See B-DEC-018 for the full finding.

Deliberately does not import anything from `core.*` -- this module
stays entirely within neptune's own package, matching the same
boundary discipline as PROVIDER_CONTRACT (no foreign SDK/package
leaking into Neptune's own contracts). It satisfies ToolPort
structurally (duck typing), the same way Neptune's own adapters
satisfy Protocols without inheriting a base class.
"""

from __future__ import annotations

import itertools
from typing import Any

from neptune.core.contracts.tool_execution import ToolCall, ToolExecutor, ToolOutcome


class ToolPortAdapter:
    """One instance is bound to one (task_id, session_id) -- construct a
    fresh instance per Runtime/process, exactly as GroqAdapter or any
    other Neptune ProviderAdapter is constructed fresh per use. Holding
    no cross-process state is what makes "fresh process resumes
    correctly" provable at all (B-006 requirement 3/4)."""

    def __init__(self, executor: ToolExecutor, task_id: str, session_id: str) -> None:
        self._executor = executor
        self._task_id = task_id
        self._session_id = session_id
        self._call_counter = itertools.count(1)

    def execute(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        call_id = f"{self._session_id}-call-{next(self._call_counter)}"
        # Core's ToolPort does not pass a turn_id through -- see module
        # docstring. "pending-turn" is a placeholder satisfying
        # ToolCall's required field; it is not used for routing or
        # dedup logic anywhere (that's Core's job, via Turn records).
        turn_id = f"{self._session_id}-pending-turn"

        call = ToolCall(
            call_id=call_id,
            tool_name=tool_call.get("tool_name", ""),
            arguments=tool_call.get("args") or {},
            task_id=self._task_id,
            session_id=self._session_id,
            turn_id=turn_id,
        )
        result = self._executor.execute(call)

        # "status" must be exactly "ok" or "error" -- RuntimeDriver.
        # tool_failed() checks observation.get("status") == "error"
        # (driver.py), so this adapter must speak that convention to
        # integrate correctly, same as FakeToolPort already does.
        return {
            "tool_name": result.tool_name,
            "status": "ok" if result.outcome == ToolOutcome.SUCCESS else "error",
            "outcome": result.outcome.value,
            "result": result.output,
            "error_message": result.error_message,
        }
