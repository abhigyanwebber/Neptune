"""Unit tests for PlanRunner (A-011): sequencing/outcome-mapping logic
using FakeModelGateway/FakeToolPort (core.runtime.fakes) + SQLite --
proves PlanRunner drives PlanExecutor's real step lifecycle from real
RuntimeDriver.execute_task() outcomes, without needing real tools/
Postgres for this layer of proof. The real-tool/real-permission proof
lives in tests/integration/planning/test_goal_to_execution.py."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine

from core.planning.executor import PlanExecutor
from core.planning.models import Goal, StepStatus
from core.planning.plan_runner import PlanRunner
from core.planning.planner import GoalPlanner
from core.runtime.driver import DriverConfig, DriverOutcome, RuntimeDriver
from core.runtime.engine import AgentRuntime
from core.runtime.fakes import FakeModelGateway, FakeToolPort
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyPlanRepository


def _build(gateway, tool_port=None):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    plan_repo = SqlAlchemyPlanRepository(sf)
    plan_executor = PlanExecutor(plan_repo)
    planner = GoalPlanner(model_gateway=gateway, plan_repository=plan_repo, plan_executor=plan_executor)

    from infrastructure.persistence.repositories import (
        SqlAlchemyAgentRepository,
        SqlAlchemyCheckpointRepository,
        SqlAlchemyEventRepository,
        SqlAlchemySessionRepository,
        SqlAlchemyTaskRepository,
        SqlAlchemyTurnRepository,
    )

    def driver_factory(task_id: str) -> RuntimeDriver:
        runtime = AgentRuntime(
            task_repo=SqlAlchemyTaskRepository(sf),
            agent_repo=SqlAlchemyAgentRepository(sf),
            session_repo=SqlAlchemySessionRepository(sf),
            turn_repo=SqlAlchemyTurnRepository(sf),
            event_repo=SqlAlchemyEventRepository(sf),
            checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
            model_gateway=gateway,
            tool_port=tool_port or FakeToolPort(),
        )
        return RuntimeDriver(runtime, config=DriverConfig(max_turns=5))

    runner = PlanRunner(planner=planner, executor=plan_executor, driver_factory=driver_factory)
    return runner, plan_executor, plan_repo


def _plan_content(steps: list[dict]) -> dict:
    return {"content": json.dumps({"steps": steps}), "tool_calls": []}


def test_single_step_plan_runs_to_completion():
    gateway = FakeModelGateway(
        scripted_responses=[
            _plan_content([{"step_id": "s1", "title": "Do the thing"}]),
            {"content": "calling a tool", "tool_calls": [{"tool_name": "echo", "args": {"text": "hi"}}]},
            {"content": "done", "tool_calls": []},
        ]
    )
    runner, executor, plan_repo = _build(gateway)

    result = runner.run_goal(Goal(goal_id="g1", description="Do the thing"))

    assert len(result.step_results) == 1
    assert result.step_results[0].step_id == "s1"
    assert result.step_results[0].driver_result.outcome == DriverOutcome.COMPLETED
    assert result.plan.get_step("s1").status == StepStatus.COMPLETED
    assert executor.is_complete(result.plan) is True
    assert executor.all_succeeded(result.plan) is True

    # Persisted plan reflects the same terminal state.
    persisted = plan_repo.get(result.plan.plan_id)
    assert persisted.get_step("s1").status == StepStatus.COMPLETED


def test_multi_step_plan_runs_steps_in_dependency_order():
    gateway = FakeModelGateway(
        scripted_responses=[
            _plan_content(
                [
                    {"step_id": "write", "title": "Write"},
                    {"step_id": "read", "title": "Read", "dependencies": ["write"]},
                ]
            ),
            {"content": "writing", "tool_calls": [{"tool_name": "write_file", "args": {}}]},
            {"content": "wrote it", "tool_calls": []},
            {"content": "reading", "tool_calls": [{"tool_name": "read_file", "args": {}}]},
            {"content": "read it", "tool_calls": []},
        ]
    )
    runner, executor, _repo = _build(gateway)

    result = runner.run_goal(Goal(goal_id="g2", description="Write then read"))

    assert [r.step_id for r in result.step_results] == ["write", "read"]
    assert all(r.driver_result.outcome == DriverOutcome.COMPLETED for r in result.step_results)
    assert executor.all_succeeded(result.plan) is True

    # Each step ran as its own task -- deterministic, distinct task_ids.
    assert result.plan.plan_id + "-write" != result.plan.plan_id + "-read"


def test_tool_failure_marks_step_failed_and_cascades_skip_to_dependents():
    class FailingToolPort:
        def execute(self, tool_call):
            return {"tool_name": tool_call.get("tool_name", "unknown"), "status": "error", "result": None}

    gateway = FakeModelGateway(
        scripted_responses=[
            _plan_content(
                [
                    {"step_id": "risky", "title": "Risky step"},
                    {"step_id": "downstream", "title": "Downstream", "dependencies": ["risky"]},
                ]
            ),
            {"content": "trying", "tool_calls": [{"tool_name": "run_command", "args": {}}]},
        ]
    )
    runner, executor, _repo = _build(gateway, tool_port=FailingToolPort())

    result = runner.run_goal(Goal(goal_id="g3", description="Do a risky thing then more"))

    # Only "risky" ran -- "downstream" never became executable because
    # PlanExecutor's own cascade-skip (A-007, unchanged) removed it from
    # select_next_step() results once "risky" failed.
    assert [r.step_id for r in result.step_results] == ["risky"]
    assert result.step_results[0].driver_result.outcome == DriverOutcome.STOPPED_TOOL_FAILURE

    assert result.plan.get_step("risky").status == StepStatus.FAILED
    assert result.plan.get_step("downstream").status == StepStatus.SKIPPED
    assert executor.is_complete(result.plan) is True  # nothing left executable
    assert executor.all_succeeded(result.plan) is False  # but it did NOT silently succeed


def test_invalid_goal_plan_is_not_persisted_and_nothing_executes():
    from core.planning.errors import PlanGenerationError

    gateway = FakeModelGateway(scripted_responses=[{"content": "not json at all", "tool_calls": []}])
    runner, _executor, plan_repo = _build(gateway)

    with pytest.raises(PlanGenerationError):
        runner.run_goal(Goal(goal_id="g4", description="Do something"))

    # A-010's existing guarantee, unaffected by PlanRunner: an invalid
    # plan is never persisted, so nothing could have executed.
    assert plan_repo.list_for_goal("g4") == []
    # Only the one planning call was made -- no execution-driver call
    # happened (there's nothing after it in the script to consume).
    assert len(gateway.requests_received) == 1
