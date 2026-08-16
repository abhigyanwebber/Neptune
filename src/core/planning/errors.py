class IllegalPlanTransition(RuntimeError):
    """Raised when the executor is asked to do something the current step
    state does not allow (e.g. completing a step that was never started,
    or starting a step whose dependencies aren't all completed yet)."""


class PlanValidationError(ValueError):
    """Raised by PlanExecutor.start_plan() when a plan's step dependency
    graph is invalid (a cycle, or a dependency referencing a step_id that
    doesn't exist in the plan)."""
