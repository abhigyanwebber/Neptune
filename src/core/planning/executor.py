"""PlanExecutor: control-flow only over a Plan's steps.

Responsibilities per the A-007 brief: start a plan, select the next
executable step, mark steps completed/failed, determine plan completion.
Execution order respects step dependencies and is deterministic (steps
are considered in the order they appear in Plan.steps -- the first
PENDING step whose dependencies are all COMPLETED is selected).

This module does not decide *what* a step does, does not call a
provider, does not run a tool, and does not generate plans -- it only
moves PlanStep.status through its lifecycle and persists the result via
an injected PlanRepository (same inject-and-auto-persist pattern as
AgentRuntime, core/runtime/engine.py).

Cycle/reference validation reuses core.registry.dependency_resolution.
resolve_dependencies() unchanged (already generic over any id -> depends_on
map, not registry-specific) rather than reimplementing graph traversal.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from core.registry.dependency_resolution import (
    DependencyCycleError,
    UnresolvedDependencyError,
    resolve_dependencies,
)

from .errors import IllegalPlanTransition, PlanValidationError
from .models import Plan, PlanStep, StepStatus

if TYPE_CHECKING:  # pragma: no cover
    from core.contracts.planning import PlanRepository

_TERMINAL_STATUSES = (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)


class PlanExecutor:
    def __init__(self, plan_repository: "PlanRepository") -> None:
        self._plans = plan_repository

    # ------------------------------------------------------------------
    # Start / load
    # ------------------------------------------------------------------
    def start_plan(self, plan: Plan) -> None:
        """Validates the step dependency graph (no cycles, no references
        to nonexistent steps) and persists the plan. Does not execute
        anything -- "starting" a plan means it's now durable and ready for
        select_next_step()/start_step() to drive."""
        self._validate_dependency_graph(plan)
        self._plans.create(plan)

    def load_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    # ------------------------------------------------------------------
    # Step selection and lifecycle
    # ------------------------------------------------------------------
    def select_next_step(self, plan: Plan) -> Optional[PlanStep]:
        """Returns the first (in Plan.steps order -- deterministic) step
        that is PENDING and whose dependencies are all COMPLETED, or None
        if no step is currently executable (either the plan is done, or
        every remaining step is blocked)."""
        completed_ids = {s.step_id for s in plan.steps if s.status == StepStatus.COMPLETED}
        for step in plan.steps:
            if step.status == StepStatus.PENDING and all(
                dep in completed_ids for dep in step.dependencies
            ):
                return step
        return None

    def start_step(self, plan: Plan, step_id: str) -> PlanStep:
        step = plan.get_step(step_id)
        if step.status != StepStatus.PENDING:
            raise IllegalPlanTransition(
                f"Cannot start step {step_id}: status is {step.status.value}, not pending"
            )
        completed_ids = {s.step_id for s in plan.steps if s.status == StepStatus.COMPLETED}
        unmet = [d for d in step.dependencies if d not in completed_ids]
        if unmet:
            raise IllegalPlanTransition(f"Cannot start step {step_id}: unmet dependencies {unmet}")

        step.status = StepStatus.RUNNING
        self._plans.update(plan)
        return step

    def complete_step(self, plan: Plan, step_id: str) -> PlanStep:
        step = plan.get_step(step_id)
        if step.status not in (StepStatus.RUNNING, StepStatus.PENDING):
            raise IllegalPlanTransition(
                f"Cannot complete step {step_id}: status is {step.status.value}"
            )
        step.status = StepStatus.COMPLETED
        self._plans.update(plan)
        return step

    def fail_step(self, plan: Plan, step_id: str, cascade_skip: bool = True) -> PlanStep:
        """Marks a step FAILED. By default also cascades SKIPPED to every
        pending step that (directly or transitively) depends on it, since
        those steps can now never become executable -- this is the path
        that produces StepStatus.SKIPPED without a human/caller having to
        skip each dependent step manually."""
        step = plan.get_step(step_id)
        if step.status not in (StepStatus.RUNNING, StepStatus.PENDING):
            raise IllegalPlanTransition(f"Cannot fail step {step_id}: status is {step.status.value}")
        step.status = StepStatus.FAILED
        if cascade_skip:
            self._cascade_skip(plan, step_id)
        self._plans.update(plan)
        return step

    def skip_step(self, plan: Plan, step_id: str) -> PlanStep:
        step = plan.get_step(step_id)
        if step.status in (StepStatus.COMPLETED, StepStatus.FAILED):
            raise IllegalPlanTransition(f"Cannot skip step {step_id}: status is {step.status.value}")
        step.status = StepStatus.SKIPPED
        self._plans.update(plan)
        return step

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------
    def is_complete(self, plan: Plan) -> bool:
        """True once every step has reached a terminal status (completed,
        failed, or skipped) -- i.e. there is nothing left to execute,
        regardless of whether every step succeeded."""
        return all(step.status in _TERMINAL_STATUSES for step in plan.steps)

    def all_succeeded(self, plan: Plan) -> bool:
        """True only if every step COMPLETED -- stricter than is_complete()."""
        return all(step.status == StepStatus.COMPLETED for step in plan.steps)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _cascade_skip(self, plan: Plan, failed_step_id: str) -> None:
        blocked_ids = {failed_step_id}
        changed = True
        while changed:
            changed = False
            for step in plan.steps:
                if step.status == StepStatus.PENDING and any(
                    dep in blocked_ids for dep in step.dependencies
                ):
                    step.status = StepStatus.SKIPPED
                    blocked_ids.add(step.step_id)
                    changed = True

    def _validate_dependency_graph(self, plan: Plan) -> None:
        dependency_map = {s.step_id: list(s.dependencies) for s in plan.steps}
        try:
            for step_id in dependency_map:
                resolve_dependencies(step_id, dependency_map)
        except DependencyCycleError as exc:
            raise PlanValidationError(f"Plan {plan.plan_id} has a dependency cycle: {exc}") from exc
        except UnresolvedDependencyError as exc:
            raise PlanValidationError(
                f"Plan {plan.plan_id} references an unknown step: {exc}"
            ) from exc
