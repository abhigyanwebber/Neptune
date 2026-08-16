"""Standalone script invoked as a SEPARATE OS process by
test_plan_recovery.py.

    python _plan_recovery_script.py step1 <plan_id>
        -> creates a 2-step plan, starts it (persists), selects and
           completes step 1, then this process exits (dies).
    python _plan_recovery_script.py step2_and_complete <plan_id>
        -> a brand-new process reconnects, loads the plan purely from
           Postgres, selects and completes step 2, and confirms the plan
           is complete. Prints the result as JSON.

This is the literal "Plan -> Execute Step 1 -> Persist -> Reload ->
Execute Step 2 -> Complete" demonstration the A-007 brief asks for, using
two genuinely separate OS processes -- not a fresh in-memory object in the
same test process.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from config.settings import get_database_url  # noqa: E402
from core.planning.executor import PlanExecutor  # noqa: E402
from core.planning.models import Plan, PlanStep, StepStatus  # noqa: E402
from infrastructure.persistence.database import (  # noqa: E402
    create_all_tables,
    make_engine,
    make_session_factory,
)
from infrastructure.persistence.repositories import SqlAlchemyPlanRepository  # noqa: E402


def _build_executor() -> PlanExecutor:
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return PlanExecutor(SqlAlchemyPlanRepository(sf))


def do_step1(plan_id: str) -> None:
    executor = _build_executor()
    plan = Plan(
        plan_id=plan_id,
        goal_id=f"{plan_id}-goal",
        steps=[
            PlanStep(step_id="step-1", title="First step", capability_id="reasoning"),
            PlanStep(
                step_id="step-2",
                title="Second step",
                capability_id="coding",
                dependencies=["step-1"],
            ),
        ],
    )
    executor.start_plan(plan)  # validates + persists (Persist)

    next_step = executor.select_next_step(plan)
    assert next_step is not None and next_step.step_id == "step-1"
    executor.start_step(plan, "step-1")
    executor.complete_step(plan, "step-1")  # persisted via repository.update()

    print(
        json.dumps(
            {
                "step1_status": plan.get_step("step-1").status.value,
                "step2_status": plan.get_step("step-2").status.value,
                "is_complete": executor.is_complete(plan),
            }
        )
    )


def do_step2_and_complete(plan_id: str) -> None:
    executor = _build_executor()

    # Reload: a brand-new process, brand-new PlanExecutor/PlanRepository,
    # loading state purely from Postgres -- no shared memory with do_step1.
    plan = executor.load_plan(plan_id)
    assert plan is not None, "plan not found -- persistence from phase 1 failed"
    assert plan.get_step("step-1").status == StepStatus.COMPLETED

    next_step = executor.select_next_step(plan)
    assert next_step is not None and next_step.step_id == "step-2"
    executor.start_step(plan, "step-2")
    executor.complete_step(plan, "step-2")

    print(
        json.dumps(
            {
                "step1_status": plan.get_step("step-1").status.value,
                "step2_status": plan.get_step("step-2").status.value,
                "is_complete": executor.is_complete(plan),
                "all_succeeded": executor.all_succeeded(plan),
            }
        )
    )


if __name__ == "__main__":
    mode = sys.argv[1]
    plan_id = sys.argv[2]
    if mode == "step1":
        do_step1(plan_id)
    elif mode == "step2_and_complete":
        do_step2_and_complete(plan_id)
    else:
        raise SystemExit(f"Unknown mode: {mode}")
