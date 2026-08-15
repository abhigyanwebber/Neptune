"""Tool execution boundary tests (B-004).

Covers: tool lookup, missing tool, invalid payload, successful
execution, timeout, output-size limit, and attribution propagation.
All unit-level -- no live provider or network involved.
"""

from __future__ import annotations

import time

import pytest

from neptune.core.contracts.model_gateway import ToolDefinition
from neptune.core.contracts.tool_execution import ToolCall, ToolInputError, ToolOutcome
from neptune.infrastructure.tools.echo_tool import EchoTool
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter


def make_call(tool_name: str = "echo", arguments: dict | None = None) -> ToolCall:
    return ToolCall(
        call_id="call-1",
        tool_name=tool_name,
        arguments=arguments if arguments is not None else {"text": "hello"},
        task_id="task-1",
        session_id="session-1",
        turn_id="turn-1",
    )


@pytest.fixture
def registry() -> ToolRegistryAdapter:
    return ToolRegistryAdapter([EchoTool()])


@pytest.fixture
def executor(registry: ToolRegistryAdapter) -> ToolExecutorService:
    return ToolExecutorService(registry, timeout_seconds=1.0)


# --- tool lookup ---

def test_registry_lookup_returns_registered_tool(registry: ToolRegistryAdapter) -> None:
    tool = registry.get("echo")
    assert tool.name == "echo"


def test_registry_list_tools_returns_definitions(registry: ToolRegistryAdapter) -> None:
    definitions = registry.list_tools()
    assert len(definitions) == 1
    assert isinstance(definitions[0], ToolDefinition)
    assert definitions[0].name == "echo"


# --- missing tool ---

def test_missing_tool_returns_not_found_outcome(executor: ToolExecutorService) -> None:
    result = executor.execute(make_call(tool_name="does_not_exist"))
    assert result.outcome == ToolOutcome.NOT_FOUND
    assert result.error_message is not None
    assert "does_not_exist" in result.error_message


def test_missing_tool_does_not_raise(executor: ToolExecutorService) -> None:
    # execute() must never propagate ToolNotFoundError -- only return it as data.
    result = executor.execute(make_call(tool_name="also_missing"))
    assert result.output is None


# --- invalid payload ---

def test_missing_required_argument_returns_error_outcome(executor: ToolExecutorService) -> None:
    result = executor.execute(make_call(arguments={}))
    assert result.outcome == ToolOutcome.ERROR
    assert "text" in (result.error_message or "")


def test_wrong_argument_type_returns_error_outcome(executor: ToolExecutorService) -> None:
    result = executor.execute(make_call(arguments={"text": 12345}))
    assert result.outcome == ToolOutcome.ERROR
    assert "string" in (result.error_message or "")


def test_echo_tool_raises_tool_input_error_directly() -> None:
    """Unit-level check on the tool itself, not just through the executor."""
    tool = EchoTool()
    with pytest.raises(ToolInputError):
        tool.execute({})


# --- successful execution ---

def test_successful_echo_execution(executor: ToolExecutorService) -> None:
    result = executor.execute(make_call(arguments={"text": "hello"}))
    assert result.outcome == ToolOutcome.SUCCESS
    assert result.output == {"echo": "hello"}
    assert result.error_message is None
    assert result.duration_ms >= 0


def test_result_attribution_matches_call(executor: ToolExecutorService) -> None:
    call = make_call()
    result = executor.execute(call)
    assert result.call_id == call.call_id
    assert result.tool_name == call.tool_name
    assert result.task_id == call.task_id
    assert result.session_id == call.session_id
    assert result.turn_id == call.turn_id


# --- timeout ---

class _SlowTool:
    name = "slow"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(name=self.name, description="sleeps longer than the timeout")

    def execute(self, arguments: dict) -> dict:
        del arguments
        time.sleep(5)
        return {"done": True}


def test_slow_tool_times_out() -> None:
    registry = ToolRegistryAdapter([_SlowTool()])
    executor = ToolExecutorService(registry, timeout_seconds=0.1)
    result = executor.execute(make_call(tool_name="slow", arguments={}))
    assert result.outcome == ToolOutcome.TIMEOUT
    assert "0.1" in (result.error_message or "")


# --- output size limit ---

class _HugeOutputTool:
    name = "huge"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(name=self.name, description="returns an oversized payload")

    def execute(self, arguments: dict) -> dict:
        del arguments
        return {"data": "x" * 1000}


def test_oversized_output_returns_error() -> None:
    registry = ToolRegistryAdapter([_HugeOutputTool()])
    executor = ToolExecutorService(registry, max_output_bytes=100)
    result = executor.execute(make_call(tool_name="huge", arguments={}))
    assert result.outcome == ToolOutcome.ERROR
    assert "exceeds limit" in (result.error_message or "")


# --- unhandled exceptions never escape execute() ---

class _BrokenTool:
    name = "broken"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(name=self.name, description="always raises a bug, not ToolInputError")

    def execute(self, arguments: dict) -> dict:
        del arguments
        raise RuntimeError("some unrelated programming bug")


def test_unhandled_tool_exception_is_normalized_not_raised() -> None:
    registry = ToolRegistryAdapter([_BrokenTool()])
    executor = ToolExecutorService(registry)
    result = executor.execute(make_call(tool_name="broken", arguments={}))
    assert result.outcome == ToolOutcome.ERROR
    assert "some unrelated programming bug" in (result.error_message or "")
