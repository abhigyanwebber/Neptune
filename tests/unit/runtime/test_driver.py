"""Unit tests for RuntimeDriver: completion path, tool-call continuation
path, max-round termination, and failed-tool path. SQLite + fakes, no
Docker needed."""
from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine

from core.runtime.driver import DriverConfig, DriverOutcome, RuntimeDriver
from core.runtime.engine import AgentRuntime
from core.runtime.fakes import FakeModelGateway, FakeToolPort
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyAgentRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyTurnRepository,
)


class AlwaysFailToolPort:
    """Test double for a tool that always reports failure. Kept local to
    this test file rather than added to core/runtime/fakes.py, since
    driver.py's scope is the driver only -- not new tool implementations."""

    def __init__(self) -> None:
        self.calls_received: list[dict[str, Any]] = []

    def execute(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        self.calls_received.append(tool_call)
        return {"status": "error", "error": "simulated tool failure"}


def _build_runtime(gateway, tool_port) -> AgentRuntime:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return AgentRuntime(
        task_repo=SqlAlchemyTaskRepository(sf),
        agent_repo=SqlAlchemyAgentRepository(sf),
        session_repo=SqlAlchemySessionRepository(sf),
        turn_repo=SqlAlchemyTurnRepository(sf),
        event_repo=SqlAlchemyEventRepository(sf),
        checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
        model_gateway=gateway,
        tool_port=tool_port,
    )


def test_completion_path_single_turn():
    gateway = FakeModelGateway(scripted_responses=[{"content": "done", "tool_calls": []}])
    runtime = _build_runtime(gateway, FakeToolPort())
    driver = RuntimeDriver(runtime)

    result = driver.execute_task("task-complete")

    assert result.outcome == DriverOutcome.COMPLETED
    assert len(result.turns_run) == 1
    assert result.task is not None
    assert result.task.status.value == "completed"
    assert result.last_checkpoint is not None


def test_tool_call_continuation_path():
    gateway = FakeModelGateway(
        scripted_responses=[
            {"content": "checking", "tool_calls": [{"tool_name": "read_file", "args": {}}]},
            {"content": "done", "tool_calls": []},
        ]
    )
    tools = FakeToolPort()
    runtime = _build_runtime(gateway, tools)
    driver = RuntimeDriver(runtime)

    result = driver.execute_task("task-continue")

    assert result.outcome == DriverOutcome.COMPLETED
    assert len(result.turns_run) == 2
    assert result.turns_run[0].tool_calls  # first turn had a tool call
    assert not result.turns_run[1].tool_calls  # second turn was final
    assert len(tools.calls_received) == 1
    assert result.task.status.value == "completed"


def test_max_round_termination():
    gateway = FakeModelGateway(
        default_response_fn=lambda req: {
            "content": "still working",
            "tool_calls": [{"tool_name": "read_file", "args": {}}],
        }
    )
    runtime = _build_runtime(gateway, FakeToolPort())
    driver = RuntimeDriver(runtime, config=DriverConfig(max_turns=3))

    result = driver.execute_task("task-maxrounds")

    assert result.outcome == DriverOutcome.STOPPED_MAX_TURNS
    assert len(result.turns_run) == 3
    assert result.task is None  # never completed


def test_failed_tool_path():
    gateway = FakeModelGateway(
        scripted_responses=[
            {"content": "trying", "tool_calls": [{"tool_name": "broken_tool", "args": {}}]},
        ]
    )
    runtime = _build_runtime(gateway, AlwaysFailToolPort())
    driver = RuntimeDriver(runtime)

    result = driver.execute_task("task-toolfail")

    assert result.outcome == DriverOutcome.STOPPED_TOOL_FAILURE
    assert len(result.turns_run) == 1
    assert result.task is None


def test_should_complete_and_should_continue_are_complementary_for_normal_turns():
    gateway = FakeModelGateway(scripted_responses=[{"content": "done", "tool_calls": []}])
    runtime = _build_runtime(gateway, FakeToolPort())
    driver = RuntimeDriver(runtime)
    result = driver.execute_task("task-policy-check")

    turn = result.turns_run[0]
    assert RuntimeDriver.should_complete(turn) is True
    assert RuntimeDriver.should_continue(turn) is False
    assert RuntimeDriver.tool_failed(turn) is False


def test_execute_until_stop_on_nonexistent_task_raises():
    from core.runtime.errors import IllegalRuntimeTransition

    gateway = FakeModelGateway(scripted_responses=[{"content": "done", "tool_calls": []}])
    runtime = _build_runtime(gateway, FakeToolPort())
    driver = RuntimeDriver(runtime)

    # resume() (called internally by execute_until_stop) raises for a task
    # that was never created -- the driver doesn't swallow that, since a
    # missing task is a caller error, not a "nothing to resume" state.
    with pytest.raises(IllegalRuntimeTransition):
        driver.execute_until_stop("nonexistent-task")


def test_checkpoint_every_zero_disables_periodic_checkpoints_but_completion_still_checkpoints():
    gateway = FakeModelGateway(
        scripted_responses=[
            {"content": "checking", "tool_calls": [{"tool_name": "read_file", "args": {}}]},
            {"content": "done", "tool_calls": []},
        ]
    )
    runtime = _build_runtime(gateway, FakeToolPort())
    driver = RuntimeDriver(runtime, config=DriverConfig(checkpoint_every=0))

    result = driver.execute_task("task-no-periodic-checkpoint")

    assert result.outcome == DriverOutcome.COMPLETED
    assert result.last_checkpoint is not None
    assert result.last_checkpoint.label == "final"
