"""Adapter satisfying Claude A's core.contracts.gateway.ModelGatewayPort
by wrapping Neptune's real ModelGatewayService (Gateway/Router/
ProviderAdapter chain, B-001..B-003), now backed by the canonical
registry via CanonicalRegistryCandidateSource instead of the deprecated
YAML ModelRegistry (C-005's cutover plan, item 3 of this task).

Same seam pattern ToolPortAdapter already proved for tools
(B-006/ADR-044): a stateless adapter, constructed fresh per Runtime/
process, that translates Core's opaque dict convention into Neptune's
own richer contract types and back, without modifying either contract.
`ModelGatewayPort.send()` is NOT documented as "never raises" the way
`ToolPort.execute()` explicitly is (core/contracts/tools.py), and
Core's own call site (core/runtime/engine.py's run_turn(),
`response = self._gateway.send(context)`) has no try/except around it
-- so a raised exception here would leave a Turn stuck in
AWAITING_MODEL status rather than completing. This adapter therefore
follows the same "never raise, return structured data" convention
ToolPort already established, even though ModelGatewayPort's docstring
doesn't spell it out: on failure it returns a response dict carrying a
normalized `error` key rather than raising, so a Turn always reaches
COMPLETED status with the failure preserved in `turn.model_response`
(opaque to Core either way). See B-DEC entry for this task for the
full reasoning -- this is a deliberate architectural choice, not an
implementation detail, per B-008's own "stop and document" guidance.
This module deliberately does NOT import core.contracts.gateway (or
anything else from core.*) -- ModelGatewayAdapter satisfies
ModelGatewayPort structurally (duck typing), the same boundary
discipline ToolPortAdapter already established (B-006/ADR-044): this
module stays entirely within neptune's own package.
"""
from __future__ import annotations

import itertools

from neptune.application.gateway_service import ModelGatewayService
from neptune.core.contracts.model_gateway import (
    ContextMessage,
    ModelError,
    ModelGatewayError,
    ModelRequest,
    ModelResult,
)
from neptune.core.domain import Capability


_DEFAULT_CAPABILITY = Capability.CODING
# Core's context dict (core/runtime/context.py::assemble_context) has no
# capability concept at all -- known limitation, not silently hidden
# (B-008 requires documenting remaining legacy/scope gaps rather than
# hiding them). Callers can override per-task via
# Task.constraints["capability"] (a plain string, translated the same
# way CanonicalRegistryCandidateSource translates it); absent that, this
# default is used. CODING chosen because it is one of the seeded Groq
# model's actual capabilities (06_REGISTRIES/data/models.yaml), so the
# default is guaranteed resolvable against the one provider Neptune has
# today, not an arbitrary placeholder.

_MAX_RECENT_EVENTS_IN_PROMPT = 5


class ModelGatewayAdapter:
    """One instance is bound to one (task_id, session_id) -- construct a
    fresh instance per Runtime/process, same lifecycle discipline as
    ToolPortAdapter and every Neptune ProviderAdapter."""

    def __init__(
        self,
        gateway: ModelGatewayService,
        task_id: str,
        session_id: str,
    ) -> None:
        self._gateway = gateway
        self._task_id = task_id
        self._session_id = session_id
        self._call_counter = itertools.count(1)

    def send(self, request: dict) -> dict:
        turn_id = f"{self._session_id}-pending-turn"
        # Core's ToolPort/ModelGatewayPort dicts don't carry a turn_id
        # either -- same placeholder pattern as ToolPortAdapter
        # (ADR-044), for the same reason: it satisfies ModelRequest's
        # required field without claiming a correlation Core never
        # actually provides.
        model_request = self._translate_request(request, turn_id)

        try:
            result = self._gateway.infer(model_request)
        except ModelGatewayError as exc:
            return self._error_response(exc.error)

        return self._translate_response(result)

    def _translate_request(self, request: dict, turn_id: str) -> ModelRequest:
        requirements = request.get("requirements") or []
        constraints = request.get("constraints") or {}
        recent_events = request.get("recent_events") or []

        capability_override = constraints.get("capability")
        if capability_override:
            capabilities = [Capability(capability_override)]
        else:
            capabilities = [_DEFAULT_CAPABILITY]

        prompt_lines: list[str] = []
        if requirements:
            prompt_lines.append("Requirements: " + "; ".join(requirements))
        for event in recent_events[-_MAX_RECENT_EVENTS_IN_PROMPT:]:
            prompt_lines.append(f"[{event.get('event_type')}] {event.get('payload')}")
        prompt = "\n".join(prompt_lines) or "Proceed."

        return ModelRequest(
            task_id=request.get("task_id") or self._task_id,
            session_id=request.get("session_id") or self._session_id,
            turn_id=turn_id,
            capabilities=capabilities,
            context=[ContextMessage(role="user", content=prompt)],
        )

    def _translate_response(self, result: ModelResult) -> dict:
        return {
            "content": result.output_text,
            "tool_calls": [
                {"tool_name": intent.tool_name, "args": intent.arguments}
                for intent in result.tool_intents
            ],
            # Additional, non-authoritative metadata Core is free to
            # ignore (opaque-dict convention, core/contracts/gateway.py)
            # -- included because ModelResult already has it and B-008
            # item "preserve correlation/request metadata" implies not
            # discarding information Neptune already computed.
            "model_id": result.selected_model.model_id,
            "provider_id": result.selected_model.provider_id,
            "correlation_id": result.correlation_id,
            "usage": result.usage.model_dump() if result.usage else None,
            "latency_ms": result.latency_ms,
        }

    def _error_response(self, error: ModelError) -> dict:
        """Never raises. Returns a plain dict carrying a normalized
        `error` key -- no raw provider exception, HTTP detail, or SDK
        type crosses this boundary. Core stores this as opaque
        turn.model_response data and completes the Turn normally
        (tool_calls is empty, so no further tool round happens)."""
        return {
            "content": None,
            "tool_calls": [],
            "error": {
                "error_type": error.error_type.value,
                "message": error.message,
                "retriable": error.retriable,
                "provider_id": error.provider_id,
            },
        }
