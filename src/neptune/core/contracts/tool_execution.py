"""Tool Execution contract (TOOL_CONTRACT.md).

Implements the frozen contract's responsibilities: describe a
capability (reuses ToolDefinition from model_gateway.py -- no
duplicate type), validate inputs, execute within a bounded envelope,
return structured success/error information, expose timeout behavior.

Explicitly NOT this module's job (TOOL_CONTRACT non-responsibilities):
  - deciding whether the agent is authorized (PERMISSION_CONTRACT,
    not built here -- B-004 is scoped to the execution boundary only);
  - choosing the model (ROUTER_CONTRACT);
  - storing arbitrary agent memory.

Invariants enforced by these shapes:
  1. Tool existence does not grant permission -- ToolExecutor executes
     unconditionally once called; it is the Runtime's job (not
     built here) to have already made the authorization decision
     before calling execute().
  2. External side effects are attributable to a task/session/agent --
     ToolCall/ToolResult both carry task_id/session_id/turn_id.
  3. Tool output must have practical size/time limits -- enforced by
     ToolExecutor implementations (deferred here as a Protocol
     concern; concrete limits live in infrastructure, per
     TOOL_CONTRACT's "Deferred: timeout defaults").
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from neptune.core.contracts.model_gateway import ToolDefinition


class ToolCall(BaseModel):
    """A request to execute one tool, already authorized by the
    Runtime before reaching the executor (invariant 1 -- tool
    existence/availability is not itself a permission grant, and this
    type does not attempt to make that decision)."""

    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    task_id: str
    session_id: str
    turn_id: str


class ToolOutcome(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"


class ToolResult(BaseModel):
    """Structured success/error information (TOOL_CONTRACT
    responsibility). Never raises past the executor boundary --
    failures are represented as data, not exceptions, so a Runtime
    can always inspect what happened."""

    call_id: str
    tool_name: str
    outcome: ToolOutcome
    output: dict | None = None
    error_message: str | None = None
    duration_ms: float
    task_id: str
    session_id: str
    turn_id: str


class ToolNotFoundError(Exception):
    """Raised by a ToolRegistry when a requested tool isn't
    registered. An executor must catch this and translate it into a
    ToolResult(outcome=NOT_FOUND) -- it must never propagate past the
    execute() boundary."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"tool not found: {tool_name}")
        self.tool_name = tool_name


class ToolInputError(Exception):
    """Raised by a Tool implementation when arguments fail validation.
    Caught by the executor and translated into
    ToolResult(outcome=ERROR) -- never propagated raw."""


@runtime_checkable
class Tool(Protocol):
    """One executable capability. Structurally identical in spirit to
    ProviderAdapter: a conforming class needs no base class."""

    name: str

    def definition(self) -> ToolDefinition:
        """Describe this capability (TOOL_CONTRACT responsibility)."""
        ...

    def execute(self, arguments: dict) -> dict:
        """Validate inputs and execute within the permitted boundary.
        Raises ToolInputError for invalid arguments. Must not itself
        decide authorization (non-responsibility) or persist
        arbitrary memory (non-responsibility)."""
        ...


@runtime_checkable
class ToolRegistry(Protocol):
    """Resolves tool names to Tool implementations."""

    def get(self, name: str) -> Tool:
        """Raises ToolNotFoundError if unregistered."""
        ...

    def list_tools(self) -> list[ToolDefinition]:
        ...


@runtime_checkable
class ToolExecutor(Protocol):
    """`execute(call: ToolCall) -> ToolResult`. Always returns a
    ToolResult -- outcome/error_message carry failure information,
    per TOOL_CONTRACT's "return structured success/error information"
    responsibility. Never raises for tool-level failures (missing
    tool, invalid input, timeout); may raise only for programmer
    errors outside the tool boundary (e.g. a malformed ToolCall that
    fails Pydantic validation before construction)."""

    def execute(self, call: ToolCall) -> ToolResult:
        ...
