"""Unit tests for GoalPlanner (A-010): valid model output -> Plan,
malformed-output rejection, invalid references, dependency cycles,
persistence, and PlanExecutor compatibility. SQLite + FakeModelGateway,
no Docker/Groq needed."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine

from core.planning.errors import PlanGenerationError, PlanValidationError
from core.planning.executor import PlanExecutor
from core.planning.models import Goal, StepStatus
from core.planning.planner import GoalPlanner
from core.runtime.fakes import FakeModelGateway
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyPlanRepository


def _build(gateway):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    repo = SqlAlchemyPlanRepository(sf)
    executor = PlanExecutor(repo)
    planner = GoalPlanner(model_gateway=gateway, plan_repository=repo, plan_executor=executor)
    return planner, repo, executor


# ---------------------------------------------------------------------------
# 1. Valid model output -> persisted Plan
# ---------------------------------------------------------------------------

def test_valid_model_output_produces_persisted_plan():
    content = json.dumps(
        {
            "steps": [
                {"step_id": "write", "title": "Write file"},
                {"step_id": "read", "title": "Read file", "dependencies": ["write"]},
            ]
        }
    )
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    plan = planner.plan_goal(Goal(goal_id="g1", description="Write then read a file"))

    assert plan.goal_id == "g1"
    assert [s.step_id for s in plan.steps] == ["write", "read"]
    assert plan.get_step("read").dependencies == ["write"]
    assert all(s.status == StepStatus.PENDING for s in plan.steps)

    persisted = repo.get(plan.plan_id)
    assert persisted is not None
    assert [s.step_id for s in persisted.steps] == ["write", "read"]


def test_code_fenced_json_is_stripped_and_parsed():
    content = "```json\n" + json.dumps({"steps": [{"step_id": "s1", "title": "Only step"}]}) + "\n```"
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, _repo, _executor = _build(gateway)

    plan = planner.plan_goal(Goal(goal_id="g-fenced", description="Do one thing"))

    assert [s.step_id for s in plan.steps] == ["s1"]


# ---------------------------------------------------------------------------
# 2. Malformed output rejection
# ---------------------------------------------------------------------------

def test_non_json_content_rejected():
    gateway = FakeModelGateway(scripted_responses=[{"content": "sure, here's a plan: do stuff", "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanGenerationError):
        planner.plan_goal(Goal(goal_id="g2", description="Do something"))
    assert repo.list_for_goal("g2") == []


def test_missing_steps_key_rejected():
    gateway = FakeModelGateway(scripted_responses=[{"content": json.dumps({"not_steps": []}), "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanGenerationError):
        planner.plan_goal(Goal(goal_id="g3", description="Do something"))
    assert repo.list_for_goal("g3") == []


def test_empty_steps_list_rejected():
    gateway = FakeModelGateway(scripted_responses=[{"content": json.dumps({"steps": []}), "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanGenerationError):
        planner.plan_goal(Goal(goal_id="g4", description="Do something"))
    assert repo.list_for_goal("g4") == []


def test_step_missing_required_field_rejected():
    content = json.dumps({"steps": [{"title": "No step_id here"}]})
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanGenerationError):
        planner.plan_goal(Goal(goal_id="g5", description="Do something"))
    assert repo.list_for_goal("g5") == []


def test_duplicate_step_id_rejected():
    content = json.dumps(
        {"steps": [{"step_id": "s1", "title": "First"}, {"step_id": "s1", "title": "Dupe"}]}
    )
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanGenerationError):
        planner.plan_goal(Goal(goal_id="g6", description="Do something"))
    assert repo.list_for_goal("g6") == []


def test_gateway_error_response_rejected_as_generation_error():
    gateway = FakeModelGateway(
        scripted_responses=[{"content": None, "tool_calls": [], "error": {"message": "boom"}}]
    )
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanGenerationError):
        planner.plan_goal(Goal(goal_id="g7", description="Do something"))
    assert repo.list_for_goal("g7") == []


def test_empty_goal_description_rejected_before_calling_gateway():
    gateway = FakeModelGateway(scripted_responses=[{"content": "unused", "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanValidationError):
        planner.plan_goal(Goal(goal_id="g8", description="   "))
    assert gateway.requests_received == []
    assert repo.list_for_goal("g8") == []


# ---------------------------------------------------------------------------
# 3. Invalid references / dependency cycles (delegated to PlanExecutor)
# ---------------------------------------------------------------------------

def test_invalid_dependency_reference_rejected():
    content = json.dumps({"steps": [{"step_id": "a", "title": "A", "dependencies": ["nonexistent"]}]})
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanValidationError):
        planner.plan_goal(Goal(goal_id="g9", description="Do something"))
    assert repo.list_for_goal("g9") == []


def test_dependency_cycle_rejected():
    content = json.dumps(
        {
            "steps": [
                {"step_id": "a", "title": "A", "dependencies": ["b"]},
                {"step_id": "b", "title": "B", "dependencies": ["a"]},
            ]
        }
    )
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, repo, _executor = _build(gateway)

    with pytest.raises(PlanValidationError):
        planner.plan_goal(Goal(goal_id="g10", description="Do something"))
    assert repo.list_for_goal("g10") == []


# ---------------------------------------------------------------------------
# 4. PlanExecutor compatibility
# ---------------------------------------------------------------------------

def test_generated_plan_is_fully_drivable_by_plan_executor():
    content = json.dumps(
        {
            "steps": [
                {"step_id": "write", "title": "Write hello.txt"},
                {"step_id": "read", "title": "Read hello.txt", "dependencies": ["write"]},
            ]
        }
    )
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, _repo, executor = _build(gateway)

    plan = planner.plan_goal(Goal(goal_id="g11", description="Write then read hello.txt"))

    next_step = executor.select_next_step(plan)
    assert next_step.step_id == "write"
    executor.start_step(plan, "write")
    executor.complete_step(plan, "write")

    assert executor.select_next_step(plan).step_id == "read"
    executor.start_step(plan, "read")
    executor.complete_step(plan, "read")

    assert executor.is_complete(plan) is True
    assert executor.all_succeeded(plan) is True


# ---------------------------------------------------------------------------
# 5. Deterministic plan_id
# ---------------------------------------------------------------------------

def test_plan_id_is_deterministic_and_increments_per_goal():
    def _response():
        return {"content": json.dumps({"steps": [{"step_id": "s1", "title": "Only step"}]}), "tool_calls": []}

    gateway = FakeModelGateway(scripted_responses=[_response(), _response()])
    planner, _repo, _executor = _build(gateway)

    goal = Goal(goal_id="g12", description="Do something repeatedly")
    plan_1 = planner.plan_goal(goal)
    plan_2 = planner.plan_goal(goal)

    assert plan_1.plan_id == "g12-plan-1"
    assert plan_2.plan_id == "g12-plan-2"


# ---------------------------------------------------------------------------
# 6. Request shape sent to the gateway (opaque-dict convention)
# ---------------------------------------------------------------------------

def test_request_sent_to_gateway_carries_the_goal_description():
    content = json.dumps({"steps": [{"step_id": "s1", "title": "Only step"}]})
    gateway = FakeModelGateway(scripted_responses=[{"content": content, "tool_calls": []}])
    planner, _repo, _executor = _build(gateway)

    planner.plan_goal(Goal(goal_id="g13", description="Build a birdhouse"))

    assert len(gateway.requests_received) == 1
    request = gateway.requests_received[0]
    assert "requirements" in request
    assert "Build a birdhouse" in request["requirements"][0]
