"""Goal-to-Plan generation (A-010).

The smallest real bridge from a user goal to an existing, persisted
Neptune Plan:

    Goal -> GoalPlanner -> validated Plan -> PlanRepository -> PlanExecutor

GoalPlanner does not decompose goals itself, does not execute tools, and
does not own a runtime loop -- it makes exactly one ModelGatewayPort.send()
call, turns the response into an existing core.planning.models.Plan (never
a second Plan type), and hands it to the existing PlanExecutor.start_plan()
for the dependency-graph validation and persistence that already exists
(A-007). This module adds no new Plan/PlanStep fields and no new gateway
or provider abstraction (brief: "Do not create a second gateway or
provider abstraction").

Structured output mechanism (brief section 3): reuses the existing,
already-proven mechanism for getting model output back through
ModelGatewayPort.send() -- the response's opaque `content` string
(core/contracts/gateway.py's own docstring: "Core does not interpret
provider-specific fields, it only stores and forwards them"), the exact
same field AgentRuntime.run_turn() already reads for a final answer. The
request is built the same way core/runtime/context.py's assemble_context()
already builds one: a `requirements` list joined into a prompt by whatever
ModelGatewayPort implementation is wired in (see
neptune/infrastructure/gateway/model_gateway_adapter.py's
_translate_request(), which already turns `request["requirements"]` into
a prompt -- unchanged by this task). No tool-calling, no adapter-level
schema mechanism, and no RoutingConstraints.require_structured_output (a
declared but unimplemented field, confirmed by inspection) were needed or
added -- the brief's "if a minimal adapter-level mechanism is truly
necessary, add only that" turned out not to apply here.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .errors import PlanGenerationError, PlanValidationError
from .executor import PlanExecutor
from .models import Goal, Plan, PlanStep

if TYPE_CHECKING:  # pragma: no cover
    from core.contracts.gateway import ModelGatewayPort
    from core.contracts.planning import PlanRepository

_PLANNING_PROMPT_TEMPLATE = """Goal: {description}

Produce a plan for accomplishing this goal.

Respond with STRICT JSON ONLY -- no markdown code fences, no prose before \
or after -- matching exactly this shape:

{{"steps": [{{"step_id": "<unique short id>", "title": "<short title>", \
"description": "<optional longer description>", \
"capability_id": "<optional capability, e.g. tool_use>", \
"dependencies": ["<step_id of a prior step, if any>"]}}]}}

Rules:
- Return at least one step.
- Every step_id must be unique within the plan.
- Every value in a step's "dependencies" must be the step_id of another \
step in this same plan -- never a step_id you did not also define.
- Do not include a "status" field.
- Respond with the JSON object and nothing else."""


class GoalPlanner:
    """Goal -> Plan bridge (A-010). Depends only on the existing
    ModelGatewayPort and PlanRepository contracts plus the existing
    PlanExecutor -- no new abstraction, no infrastructure import (see
    tests/contract/test_core_provider_independence.py, which already
    statically enforces this for every file under core/, this one
    included)."""

    def __init__(
        self,
        model_gateway: "ModelGatewayPort",
        plan_repository: "PlanRepository",
        plan_executor: PlanExecutor,
    ) -> None:
        self._gateway = model_gateway
        self._plans = plan_repository
        self._executor = plan_executor

    def plan_goal(self, goal: Goal) -> Plan:
        """Turns a Goal into a persisted, executor-ready Plan, or raises
        PlanValidationError (or its PlanGenerationError subclass) without
        persisting anything. Never fabricates or repairs malformed model
        output -- a plan that doesn't parse or doesn't validate is
        rejected outright (brief section 4)."""
        if not goal.description or not goal.description.strip():
            raise PlanValidationError("Goal description must be non-empty")

        response = self._gateway.send(self._build_request(goal))
        data = self._parse_model_output(response)
        plan = self._build_plan(goal, data)

        # Reuses PlanExecutor's own, already-tested dependency-graph
        # validation (cycles, unresolved references -- core.registry.
        # dependency_resolution) and its own persistence call
        # (PlanRepository.create) rather than duplicating either. Raises
        # PlanValidationError, and persists nothing, on an invalid graph.
        self._executor.start_plan(plan)
        return plan

    # ------------------------------------------------------------------
    # Model request / response
    # ------------------------------------------------------------------
    def _build_request(self, goal: Goal) -> dict[str, Any]:
        prompt = _PLANNING_PROMPT_TEMPLATE.format(description=goal.description)
        return {"requirements": [prompt]}

    def _parse_model_output(self, response: dict[str, Any]) -> dict[str, Any]:
        content = (response or {}).get("content")
        if not content or not isinstance(content, str):
            error = (response or {}).get("error")
            raise PlanGenerationError(
                f"Model returned no usable content for plan generation"
                + (f" (gateway error: {error})" if error else "")
            )
        cleaned = _strip_code_fences(content).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise PlanGenerationError(f"Model output was not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise PlanGenerationError("Model output JSON must be an object with a 'steps' list")
        return data

    # ------------------------------------------------------------------
    # Plan construction / validation
    # ------------------------------------------------------------------
    def _build_plan(self, goal: Goal, data: dict[str, Any]) -> Plan:
        steps_data = data.get("steps")
        if not isinstance(steps_data, list) or not steps_data:
            raise PlanGenerationError("Model output must contain a non-empty 'steps' list")

        steps: list[PlanStep] = []
        seen_ids: set[str] = set()
        for index, raw_step in enumerate(steps_data):
            if not isinstance(raw_step, dict):
                raise PlanGenerationError(f"Step {index} is not a JSON object")
            try:
                step = PlanStep.from_dict(raw_step)
            except (KeyError, ValueError, TypeError) as exc:
                raise PlanGenerationError(f"Step {index} is malformed: {exc}") from exc
            if not step.step_id or not step.step_id.strip():
                raise PlanGenerationError(f"Step {index} is missing a non-empty step_id")
            if not step.title or not step.title.strip():
                raise PlanGenerationError(f"Step {index} ('{step.step_id}') is missing a non-empty title")
            if step.step_id in seen_ids:
                raise PlanGenerationError(f"Duplicate step_id in model output: {step.step_id}")
            seen_ids.add(step.step_id)
            steps.append(step)

        return Plan(plan_id=self._next_plan_id(goal.goal_id), goal_id=goal.goal_id, steps=steps)

    def _next_plan_id(self, goal_id: str) -> str:
        """Deterministic, not random: `<goal_id>-plan-<n>`, where n is one
        more than the number of plans already persisted for this goal.
        Same existing-rule pattern as Turn ids (core/runtime/engine.py:
        `f"{session_id}-turn-{next_sequence}"`) -- a sequence number
        derived from what's already durable, not a UUID."""
        existing = self._plans.list_for_goal(goal_id)
        return f"{goal_id}-plan-{len(existing) + 1}"


def _strip_code_fences(text: str) -> str:
    """Defensive formatting cleanup only -- strips a leading/trailing
    ``` or ```json fence if the model wrapped its JSON in one despite
    being told not to. This does not interpret, repair, or alter the
    JSON content itself (brief section 4: "Do not silently fabricate or
    arbitrarily repair model output") -- malformed JSON inside (or
    without) fences still fails json.loads() and is rejected."""
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[: -len("```")]
    return stripped
