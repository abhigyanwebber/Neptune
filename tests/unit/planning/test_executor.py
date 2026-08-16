"""Unit tests for PlanExecutor: single-step, multi-step sequential,
dependency graph, failed-step handling, plan completion detection, and
deterministic ordering. SQLite, no Docker needed."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from core.planning.errors import IllegalPlanTransition, PlanValidationError
from core.planning.executor import PlanExecutor
from core.planning.models import Plan, PlanStep, StepStatus
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyPlanRepository


@pytest.fixture()
def executor():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return PlanExecutor(SqlAlchemyPlanRepository(sf))


# ---------------------------------------------------------------------------
# 1. Single-step plan
# ---------------------------------------------------------------------------

def test_single_step_plan_full_lifecycle(executor):
    plan = Plan(plan_id="p1", goal_id="g1", steps=[PlanStep(step_id="s1", title="Do the thing")])
    executor.start_plan(plan)

    assert executor.is_complete(plan) is False
    next_step = executor.select_next_step(plan)
    assert next_step.step_id == "s1"

    executor.start_step(plan, "s1")
    assert plan.get_step("s1").status == StepStatus.RUNNING

    executor.complete_step(plan, "s1")
    assert plan.get_step("s1").status == StepStatus.COMPLETED
    assert executor.is_complete(plan) is True
    assert executor.all_succeeded(plan) is True
    assert executor.select_next_step(plan) is None


# ---------------------------------------------------------------------------
# 2. Multi-step sequential plan
# ---------------------------------------------------------------------------

def test_multi_step_sequential_plan(executor):
    plan = Plan(
        plan_id="p2",
        goal_id="g1",
        steps=[
            PlanStep(step_id="s1", title="First"),
            PlanStep(step_id="s2", title="Second", dependencies=["s1"]),
            PlanStep(step_id="s3", title="Third", dependencies=["s2"]),
        ],
    )
    executor.start_plan(plan)

    # s2/s3 aren't executable yet -- only s1 is.
    assert executor.select_next_step(plan).step_id == "s1"
    executor.start_step(plan, "s1")
    executor.complete_step(plan, "s1")

    assert executor.select_next_step(plan).step_id == "s2"
    executor.start_step(plan, "s2")
    executor.complete_step(plan, "s2")

    assert executor.select_next_step(plan).step_id == "s3"
    executor.start_step(plan, "s3")
    executor.complete_step(plan, "s3")

    assert executor.is_complete(plan) is True
    assert executor.all_succeeded(plan) is True


def test_cannot_start_step_before_dependency_completes(executor):
    plan = Plan(
        plan_id="p3",
        goal_id="g1",
        steps=[
            PlanStep(step_id="s1", title="First"),
            PlanStep(step_id="s2", title="Second", dependencies=["s1"]),
        ],
    )
    executor.start_plan(plan)
    with pytest.raises(IllegalPlanTransition):
        executor.start_step(plan, "s2")


# ---------------------------------------------------------------------------
# 3. Dependency graph (diamond)
# ---------------------------------------------------------------------------

def test_dependency_graph_diamond(executor):
    plan = Plan(
        plan_id="p4",
        goal_id="g1",
        steps=[
            PlanStep(step_id="root", title="Root"),
            PlanStep(step_id="left", title="Left", dependencies=["root"]),
            PlanStep(step_id="right", title="Right", dependencies=["root"]),
            PlanStep(step_id="join", title="Join", dependencies=["left", "right"]),
        ],
    )
    executor.start_plan(plan)

    executor.start_step(plan, "root")
    executor.complete_step(plan, "root")

    # Both left and right are now executable; join is not yet.
    next_step = executor.select_next_step(plan)
    assert next_step.step_id == "left"  # deterministic: declared order

    executor.start_step(plan, "left")
    executor.complete_step(plan, "left")

    # join still blocked on "right"
    assert executor.select_next_step(plan).step_id == "right"
    executor.start_step(plan, "right")
    executor.complete_step(plan, "right")

    assert executor.select_next_step(plan).step_id == "join"
    executor.start_step(plan, "join")
    executor.complete_step(plan, "join")

    assert executor.is_complete(plan) is True


def test_start_plan_rejects_cycle(executor):
    plan = Plan(
        plan_id="p5",
        goal_id="g1",
        steps=[
            PlanStep(step_id="a", title="A", dependencies=["b"]),
            PlanStep(step_id="b", title="B", dependencies=["a"]),
        ],
    )
    with pytest.raises(PlanValidationError):
        executor.start_plan(plan)


def test_start_plan_rejects_unknown_dependency(executor):
    plan = Plan(
        plan_id="p6",
        goal_id="g1",
        steps=[PlanStep(step_id="a", title="A", dependencies=["nonexistent"])],
    )
    with pytest.raises(PlanValidationError):
        executor.start_plan(plan)


# ---------------------------------------------------------------------------
# 4. Failed step handling
# ---------------------------------------------------------------------------

def test_failed_step_cascades_skip_to_dependents(executor):
    plan = Plan(
        plan_id="p7",
        goal_id="g1",
        steps=[
            PlanStep(step_id="s1", title="First"),
            PlanStep(step_id="s2", title="Second", dependencies=["s1"]),
            PlanStep(step_id="s3", title="Third", dependencies=["s2"]),
            PlanStep(step_id="independent", title="Unrelated"),
        ],
    )
    executor.start_plan(plan)
    executor.start_step(plan, "s1")
    executor.fail_step(plan, "s1")

    assert plan.get_step("s1").status == StepStatus.FAILED
    assert plan.get_step("s2").status == StepStatus.SKIPPED
    assert plan.get_step("s3").status == StepStatus.SKIPPED
    assert plan.get_step("independent").status == StepStatus.PENDING  # unaffected

    # Plan isn't complete yet -- "independent" is still pending.
    assert executor.is_complete(plan) is False
    executor.start_step(plan, "independent")
    executor.complete_step(plan, "independent")

    assert executor.is_complete(plan) is True
    assert executor.all_succeeded(plan) is False  # s1 failed


def test_fail_step_without_cascade(executor):
    plan = Plan(
        plan_id="p8",
        goal_id="g1",
        steps=[
            PlanStep(step_id="s1", title="First"),
            PlanStep(step_id="s2", title="Second", dependencies=["s1"]),
        ],
    )
    executor.start_plan(plan)
    executor.start_step(plan, "s1")
    executor.fail_step(plan, "s1", cascade_skip=False)

    assert plan.get_step("s2").status == StepStatus.PENDING  # not cascaded


def test_cannot_complete_already_completed_step(executor):
    plan = Plan(plan_id="p9", goal_id="g1", steps=[PlanStep(step_id="s1", title="First")])
    executor.start_plan(plan)
    executor.start_step(plan, "s1")
    executor.complete_step(plan, "s1")
    with pytest.raises(IllegalPlanTransition):
        executor.complete_step(plan, "s1")


# ---------------------------------------------------------------------------
# 5. Plan completion detection
# ---------------------------------------------------------------------------

def test_is_complete_false_while_steps_pending(executor):
    plan = Plan(
        plan_id="p10",
        goal_id="g1",
        steps=[PlanStep(step_id="s1", title="A"), PlanStep(step_id="s2", title="B")],
    )
    executor.start_plan(plan)
    assert executor.is_complete(plan) is False
    executor.start_step(plan, "s1")
    executor.complete_step(plan, "s1")
    assert executor.is_complete(plan) is False  # s2 still pending
    executor.start_step(plan, "s2")
    executor.complete_step(plan, "s2")
    assert executor.is_complete(plan) is True


def test_is_complete_true_with_mix_of_terminal_statuses(executor):
    plan = Plan(
        plan_id="p11",
        goal_id="g1",
        steps=[
            PlanStep(step_id="s1", title="A"),
            PlanStep(step_id="s2", title="B"),
            PlanStep(step_id="s3", title="C"),
        ],
    )
    executor.start_plan(plan)
    executor.start_step(plan, "s1")
    executor.complete_step(plan, "s1")
    executor.start_step(plan, "s2")
    executor.fail_step(plan, "s2", cascade_skip=False)
    executor.skip_step(plan, "s3")

    assert executor.is_complete(plan) is True
    assert executor.all_succeeded(plan) is False


# ---------------------------------------------------------------------------
# 7. Deterministic ordering
# ---------------------------------------------------------------------------

def test_select_next_step_is_deterministic_across_runs(executor):
    plan = Plan(
        plan_id="p12",
        goal_id="g1",
        steps=[
            PlanStep(step_id="z", title="Z"),  # declared first despite the id
            PlanStep(step_id="a", title="A"),
        ],
    )
    executor.start_plan(plan)
    # Declared order (z, a), not alphabetical -- selection must follow
    # Plan.steps order, not any implicit id sort.
    assert executor.select_next_step(plan).step_id == "z"


def test_deterministic_selection_is_stable_given_same_plan_state(executor):
    plan = Plan(
        plan_id="p13",
        goal_id="g1",
        steps=[PlanStep(step_id="s1", title="A"), PlanStep(step_id="s2", title="B")],
    )
    executor.start_plan(plan)
    first_pick = executor.select_next_step(plan)
    second_pick = executor.select_next_step(plan)
    assert first_pick.step_id == second_pick.step_id == "s1"
