"""ObservationMessageBuilder unit tests (B-005).

Covers: successful observation generation, tool failure observation
generation, malformed tool result handling, deterministic formatting.
"""

from __future__ import annotations

from neptune.application.observation_loop import ObservationMessageBuilder
from neptune.core.contracts.tool_execution import ToolOutcome, ToolResult


def make_result(**overrides) -> ToolResult:
    defaults = dict(
        call_id="call-1",
        tool_name="echo",
        outcome=ToolOutcome.SUCCESS,
        output={"echo": "hello"},
        error_message=None,
        duration_ms=1.0,
        task_id="t1",
        session_id="s1",
        turn_id="tu1",
    )
    defaults.update(overrides)
    return ToolResult(**defaults)


def test_successful_observation_generation() -> None:
    builder = ObservationMessageBuilder()
    result = make_result(outcome=ToolOutcome.SUCCESS, output={"echo": "hello"})

    message = builder.build(result)

    assert message.role == "tool"
    assert message.name == "echo"
    assert message.content == 'Tool echo returned:\n{"echo": "hello"}'


def test_tool_failure_observation_generation() -> None:
    builder = ObservationMessageBuilder()
    result = make_result(
        outcome=ToolOutcome.ERROR, output=None, error_message="missing required argument: text"
    )

    message = builder.build(result)

    assert message.role == "tool"
    assert message.content == "Tool echo failed (error): missing required argument: text"


def test_timeout_outcome_observation_generation() -> None:
    builder = ObservationMessageBuilder()
    result = make_result(
        outcome=ToolOutcome.TIMEOUT, output=None, error_message="tool 'echo' exceeded 10.0s timeout"
    )

    message = builder.build(result)

    assert message.content == "Tool echo failed (timeout): tool 'echo' exceeded 10.0s timeout"


def test_not_found_outcome_observation_generation() -> None:
    builder = ObservationMessageBuilder()
    result = make_result(
        tool_name="does_not_exist",
        outcome=ToolOutcome.NOT_FOUND,
        output=None,
        error_message="tool not found: does_not_exist",
    )

    message = builder.build(result)

    assert message.content == "Tool does_not_exist failed (not_found): tool not found: does_not_exist"


def test_malformed_tool_result_handling() -> None:
    """SUCCESS outcome with no output payload is malformed -- the
    builder must not crash, and must clearly signal the anomaly."""
    builder = ObservationMessageBuilder()
    result = make_result(outcome=ToolOutcome.SUCCESS, output=None, error_message=None)

    message = builder.build(result)

    assert "malformed" in message.content.lower()
    assert "echo" in message.content


def test_failure_with_no_error_message_still_formats_cleanly() -> None:
    builder = ObservationMessageBuilder()
    result = make_result(outcome=ToolOutcome.ERROR, output=None, error_message=None)

    message = builder.build(result)

    assert message.content == "Tool echo failed (error): no error message provided"


def test_deterministic_formatting_regardless_of_dict_key_order() -> None:
    """The exact format is deterministic: two ToolResults with the
    same content but differently-ordered dict keys must produce byte-
    identical observation text."""
    builder = ObservationMessageBuilder()
    result_a = make_result(output={"b": 2, "a": 1})
    result_b = make_result(output={"a": 1, "b": 2})

    assert builder.build(result_a).content == builder.build(result_b).content


def test_deterministic_formatting_repeated_calls_identical() -> None:
    builder = ObservationMessageBuilder()
    result = make_result()

    first = builder.build(result).content
    second = builder.build(result).content

    assert first == second
