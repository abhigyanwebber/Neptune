"""Goal-to-Execution Integration (A-011).

Closes the seam Director Review 005 identified: GoalPlanner's output
never reached AgentRuntime/RuntimeDriver. This module adds nothing new
to the execution architecture -- it is exactly what the brief asks
for, a sequencer over existing, unmodified public APIs:

    GoalPlanner.plan_goal()      (A-010, unchanged)
        -> Plan
    PlanExecutor.select_next_step() / start_step() / complete_step() /
    fail_step()                  (A-007, unchanged)
        -> drives one Plan step at a time
    RuntimeDriver.execute_task()  (A-005/A-009, unchanged)
        -> runs that step as a real, fresh task: dynamic tool offering
           (A-008), permission enforcement (B-012, inside whatever
           ToolExecutorService the caller's driver_factory wires up),
           real tool execution, checkpointing -- none of it re-
           implemented or bypassed here.

No second runtime, executor, tool registry, permission system, or
model-gateway logic is introduced. PlanRunner never imports
infrastructure or a provider SDK (see
tests/contract/test_core_provider_independence.py, which covers this
file automatically) -- it only knows about `RuntimeDriver`, the same
Core type A-009 already made per-task-constructible. How a
fully-wired RuntimeDriver for a given task_id gets built (real Groq,
real Postgres, real tool registry, real permission policy) is
entirely the caller's concern, injected as `driver_factory` -- the
same "inject a callable, own nothing about what's inside it" pattern
A-009's `context_provider` already established for exactly this
reason (keeping RuntimeDriver, and now PlanRunner, ignorant of
ToolOfferingResolver/Groq/provider adapters/permission policy
internals).

One Plan step = one fresh RuntimeDriver.execute_task() call, with its
own task_id (`f"{plan.plan_id}-{step.step_id}"`, deterministic, no
UUID) and therefore its own Task/Session/Turn/Checkpoint records --
the same "construct fresh per task" lifecycle every existing adapter
(ModelGatewayAdapter, ToolPortAdapter) already requires (see their own
docstrings). Nothing here changes what "a task" or "a session" means;
a Plan step just becomes exactly one of the tasks the runtime already
knows how to run, execute, checkpoint, and (via execute_until_stop)
resume.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from core.runtime.driver import DriverOutcome, DriverResult, RuntimeDriver

from .executor import PlanExecutor
from .models import Goal, Plan, PlanStep
from .planner import GoalPlanner

# A-009-pattern injection: the caller supplies a fully-wired
# RuntimeDriver for a given task_id (real gateway, real tool registry,
# real permission policy, real persistence -- or fakes, for a test).
# PlanRunner never constructs a RuntimeDriver, AgentRuntime, or any
# adapter itself.
DriverFactory = Callable[[str], RuntimeDriver]


@dataclass
class StepExecutionResult:
    step_id: str
    driver_result: DriverResult


@dataclass
class PlanRunResult:
    plan: Plan
    step_results: list[StepExecutionResult] = field(default_factory=list)


class PlanRunner:
    """Goal -> Plan -> real execution, using only existing, unmodified
    GoalPlanner/PlanExecutor/RuntimeDriver public APIs."""

    def __init__(
        self,
        planner: GoalPlanner,
        executor: PlanExecutor,
        driver_factory: DriverFactory,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._driver_factory = driver_factory

    def run_goal(self, goal: Goal) -> PlanRunResult:
        """Generates and persists a Plan (A-010's existing guarantee: a
        malformed/invalid plan raises PlanValidationError /
        PlanGenerationError and persists nothing -- not caught or
        altered here), then drives every executable step to real
        completion via RuntimeDriver, in PlanExecutor's own
        dependency-respecting, deterministic order."""
        plan = self._planner.plan_goal(goal)
        step_results: list[StepExecutionResult] = []

        while True:
            step = self._executor.select_next_step(plan)
            if step is None:
                # Either every step reached a terminal status, or every
                # remaining PENDING step is blocked (its dependencies
                # never completed -- e.g. cascaded to SKIPPED after an
                # earlier failure). Either way, PlanExecutor's own
                # is_complete()/all_succeeded() on the returned plan
                # tells the caller which; PlanRunner does not
                # second-guess that state machine.
                break
            step_results.append(self._run_step(plan, step, goal))

        return PlanRunResult(plan=plan, step_results=step_results)

    def _run_step(self, plan: Plan, step: PlanStep, goal: Goal) -> StepExecutionResult:
        # Existing PlanExecutor transition -- persists RUNNING, raises
        # IllegalPlanTransition if this step wasn't actually startable
        # (unmet dependency, already terminal). Not caught: a step that
        # shouldn't be running is a real error, not something to
        # silently skip.
        self._executor.start_step(plan, step.step_id)

        task_id = f"{plan.plan_id}-{step.step_id}"
        driver = self._driver_factory(task_id)

        # T2 (Review 007): every step receives the original user goal.
        # Only `requirements` reaches the model prompt (constraints are
        # used solely for the capability override; see
        # ModelGatewayAdapter._translate_request), and requirements are
        # already persisted on the Task, so this reuses the existing
        # context path -- no second context mechanism. The goal is
        # labelled as background so a step doesn't try to do the whole
        # goal itself. Not cross-step conversation memory: prior steps'
        # turns/observations are still not carried (post-MVP).
        requirements = [
            f"Overall goal (background only): {goal.description}",
            f"Your task now, this step only: {step.title}",
        ]
        if step.description:
            requirements.append(step.description)
        constraints = {"capability": step.capability_id} if step.capability_id else None

        result = driver.execute_task(task_id, requirements=requirements, constraints=constraints)

        # A provider failure is not a success (ADR-045: the gateway never
        # raises; it returns a normalized `error` key with no tool calls,
        # which RuntimeDriver reads as an ordinary "no more tool calls"
        # completion). Without this check a rate limit or outage would
        # mark every step COMPLETED having done nothing. Discovered while
        # building the CLI; RuntimeDriver itself is deliberately unchanged.
        final_response = (result.turns_run[-1].model_response or {}) if result.turns_run else {}
        provider_failed = bool(final_response.get("error"))

        if result.outcome == DriverOutcome.COMPLETED and not provider_failed:
            self._executor.complete_step(plan, step.step_id)
        else:
            # STOPPED_TOOL_FAILURE (includes a permission DENIED
            # observation -- ToolPortAdapter maps DENIED to
            # status="error" the same as any other tool failure, so
            # RuntimeDriver.tool_failed() already catches it),
            # STOPPED_MAX_TURNS, or STOPPED_NO_ACTIVE_SESSION: none of
            # these are success. Error semantics requirement: "tool
            # failures must not silently become success" / "permission
            # denial must remain a real denial/error" -- there is no
            # branch here that maps any non-COMPLETED outcome to
            # complete_step(). fail_step()'s existing cascade-skip
            # behavior (A-007, unchanged) then correctly removes any
            # dependent steps from future select_next_step() results.
            self._executor.fail_step(plan, step.step_id)

        return StepExecutionResult(step_id=step.step_id, driver_result=result)
