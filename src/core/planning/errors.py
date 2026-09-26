class IllegalPlanTransition(RuntimeError):
    """Raised when the executor is asked to do something the current step
    state does not allow (e.g. completing a step that was never started,
    or starting a step whose dependencies aren't all completed yet)."""


class PlanValidationError(ValueError):
    """Raised by PlanExecutor.start_plan() when a plan's step dependency
    graph is invalid (a cycle, or a dependency referencing a step_id that
    doesn't exist in the plan)."""


class PlanGenerationError(PlanValidationError):
    """A-010: raised by GoalPlanner when a ModelGatewayPort response
    cannot safely become a Plan -- not valid JSON, missing/empty
    'steps', a step missing a required field, or a duplicate step_id.
    Subclasses PlanValidationError (not a sibling): both mean "this
    would-be Plan is rejected, nothing was persisted," just for
    different reasons (model output shape vs. dependency graph), so a
    caller that only wants "plan generation failed" can catch
    PlanValidationError alone and get both."""
