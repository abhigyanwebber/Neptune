"""Recovery after persistence reload (requirement 6): a Plan mutated via
PlanExecutor, persisted, then reloaded through a brand-new PlanRepository
instance (simulating a fresh connection) must reflect the same step
statuses -- no in-memory state required."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from core.planning.executor import PlanExecutor
from core.planning.models import Plan, PlanStep, StepStatus
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyPlanRepository


@pytest.fixture()
def session_factory():
    # File-backed (not :memory:) so a second connection can see the same
    # data -- :memory: SQLite is private per-connection.
    import tempfile
    from pathlib import Path

    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "plan_recovery.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    create_all_tables(engine)
    return make_session_factory(engine)


def test_plan_state_reloads_correctly_via_fresh_repository_instance(session_factory):
    executor = PlanExecutor(SqlAlchemyPlanRepository(session_factory))
    plan = Plan(
        plan_id="reload-plan",
        goal_id="g1",
        steps=[
            PlanStep(step_id="s1", title="First"),
            PlanStep(step_id="s2", title="Second", dependencies=["s1"]),
        ],
    )
    executor.start_plan(plan)
    executor.start_step(plan, "s1")
    executor.complete_step(plan, "s1")

    # Simulate "reload": a brand-new PlanRepository + PlanExecutor, and a
    # brand-new in-memory Plan object loaded fresh from the DB -- not the
    # same `plan` Python object mutated above.
    fresh_executor = PlanExecutor(SqlAlchemyPlanRepository(session_factory))
    reloaded_plan = fresh_executor.load_plan("reload-plan")

    assert reloaded_plan is not None
    assert reloaded_plan.get_step("s1").status == StepStatus.COMPLETED
    assert reloaded_plan.get_step("s2").status == StepStatus.PENDING

    next_step = fresh_executor.select_next_step(reloaded_plan)
    assert next_step.step_id == "s2"

    fresh_executor.start_step(reloaded_plan, "s2")
    fresh_executor.complete_step(reloaded_plan, "s2")
    assert fresh_executor.is_complete(reloaded_plan) is True
