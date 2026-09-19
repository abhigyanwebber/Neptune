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
This module deliberately does NOT import core.contracts.gateway --
ModelGatewayAdapter satisfies ModelGatewayPort structurally (duck
typing), the same boundary discipline ToolPortAdapter already
established (B-006/ADR-044). It does import core.registry.
capability_bridge (A-008/C-006): that module is a pure str->str
translation utility with zero infrastructure/provider dependencies of
its own (core/contracts/test_core_provider_independence.py enforces
this on the core/ side), so importing it here is importing a small,
provider-neutral helper, not reaching into Core's runtime/contract
machinery the way importing core.contracts.gateway would.
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
    ToolDefinition,
)
from neptune.core.domain import Capability

from core.registry.capability_bridge import (
    RejectedExternalCapabilityError,
    UnknownExternalCapabilityError,
    translate_capability,
)


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

# B-011 finding: core.resolution.tool_offering_resolver.ToolOfferingResolver
# offers CATALOG-granularity entries (one per tool family, e.g. "filesystem"
# covering three real operations) with an empty parameters_schema -- it has
# no concept of Neptune's own operation-level tool names or JSON-schema
# argument shapes, because the canonical Tool Registry (A-003) was designed
# as vocabulary/governance metadata, not a function-calling schema source
# (confirmed by reading core/registry/tool_registry.py's own ToolDefinition
# fields: tool_id, name, capability, risk_class, depends_on, notes -- no
# parameters_schema field exists there at all). Offering "filesystem" or
# "terminal" verbatim to a real model gives it a callable name ToolExecutor
# cannot route (B-010's real tools are registered as read_file/write_file/
# list_directory/run_command) and zero argument guidance. This map expands
# each catalog family into the real, concrete ToolDefinitions B actually
# implemented, sourced from whatever the caller passes as
# concrete_tool_definitions (the same real Tool instances' own .definition()
# outputs) -- not a new tool, not a new contract, not a ToolExecutor/
# ToolPort/ModelGateway/registry change: purely a translation-layer fix
# inside this adapter, the same class of minimal fix as B-009's
# tool_choice/tool_definitions findings. Catalog entries with no real
# backing yet (browser, mcp, search) fall through to the prior
# degraded-but-harmless 1:1 translation (empty schema) unchanged -- if a
# model ever called one, ToolExecutor already returns a normal NOT_FOUND
# ToolResult (TOOL_CONTRACT), not a crash.
_CATALOG_TOOL_ID_TO_CONCRETE_NAMES: dict[str, list[str]] = {
    "filesystem": ["read_file", "write_file", "list_directory"],
    "terminal": ["run_command"],
}


class ModelGatewayAdapter:
    """One instance is bound to one (task_id, session_id) -- construct a
    fresh instance per Runtime/process, same lifecycle discipline as
    ToolPortAdapter and every Neptune ProviderAdapter.

    Tool offering (A-008): the primary source of what tools a request
    offers the model is now request['available_tools'] -- a list of
    plain canonical dicts, produced by
    core.resolution.tool_offering_resolver.ToolOfferingResolver querying
    the canonical Tool Registry fresh on every call. A caller populates
    this by passing extra_context={"available_tools": resolver.
    available_tools()} into AgentRuntime.run_turn() (an existing,
    unmodified parameter -- no Runtime change was needed). The
    constructor's `tool_definitions` parameter is preserved as a
    backward-compatible fallback, used only when request['available_tools']
    is absent -- this keeps every existing caller (including
    test_full_live_agent_loop.py, B-008/B-009) working unmodified while
    making the registry-driven path the default for any new caller. See
    ADR-046 for why a per-request mechanism was needed at all (Core's
    context dict has no native tool-availability concept)."""

    def __init__(
        self,
        gateway: ModelGatewayService,
        task_id: str,
        session_id: str,
        tool_definitions: list[ToolDefinition] | None = None,
        concrete_tool_definitions: list[ToolDefinition] | None = None,
    ) -> None:
        self._gateway = gateway
        self._task_id = task_id
        self._session_id = session_id
        self._call_counter = itertools.count(1)
        # B-011: real, richly-schema'd ToolDefinitions (e.g.
        # ReadFileTool(boundary).definition()) used to expand catalog-
        # granularity dynamic offerings into ToolExecutor-routable ones.
        # Indexed by name for the expansion lookup in _translate_request().
        self._concrete_tool_definitions_by_name = {
            d.name: d for d in (concrete_tool_definitions or [])
        }
        # B-009 finding: Core's context dict (core/runtime/context.py::
        # assemble_context) has no "tools" concept at all -- the same
        # gap already documented for "capability" above. Without this,
        # ModelRequest.tools was always [], so GroqAdapter never sent
        # a tools/tool_choice payload, yet a reasoning model
        # (openai/gpt-oss-120b) still attempted a tool call on its own,
        # which Groq correctly rejected: "Tool choice is none, but
        # model called a tool" (live 400, B-009 validation). The
        # adapter is told what tools are available at construction
        # time, the same way it's told task_id/session_id -- not a
        # Core change, not a new contract, and consistent with every
        # other Neptune adapter's "configured once per Runtime"
        # lifecycle.
        self._tool_definitions = tool_definitions or []

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
            # A-008 fix: previously `Capability(capability_override)`
            # directly, which raised an uncaught ValueError for any
            # canonical-only capability (web_search/mcp/browser/
            # terminal/memory -- see DIRECTOR_REVIEW_002.md/003.md).
            # Routed through the C-006 bridge first, and any failure
            # (unrecognized, rejected, or bridge-translated-but-still-
            # not-a-legacy-enum-member) falls back to the documented
            # default rather than propagating -- this send() call must
            # never raise (see module docstring).
            try:
                canonical_capability_id = translate_capability(capability_override)
                capabilities = [Capability(canonical_capability_id)]
            except (UnknownExternalCapabilityError, RejectedExternalCapabilityError, ValueError):
                capabilities = [_DEFAULT_CAPABILITY]
        else:
            capabilities = [_DEFAULT_CAPABILITY]

        prompt_lines: list[str] = []
        if requirements:
            prompt_lines.append("Requirements: " + "; ".join(requirements))
        for event in recent_events[-_MAX_RECENT_EVENTS_IN_PROMPT:]:
            prompt_lines.append(f"[{event.get('event_type')}] {event.get('payload')}")
        prompt = "\n".join(prompt_lines) or "Proceed."

        # A-008: dynamic, registry-driven tool offering takes precedence
        # over the static constructor list (see class docstring). B-011:
        # expanded through _CATALOG_TOOL_ID_TO_CONCRETE_NAMES so the
        # model receives real, routable, schema'd tool definitions
        # rather than catalog-family placeholders (see module constant
        # docstring above for the full finding).
        dynamic_offerings = request.get("available_tools")
        if dynamic_offerings is not None:
            tools = _offering_dicts_to_tool_definitions(
                dynamic_offerings, self._concrete_tool_definitions_by_name
            )
        else:
            tools = self._tool_definitions

        return ModelRequest(
            task_id=request.get("task_id") or self._task_id,
            session_id=request.get("session_id") or self._session_id,
            turn_id=turn_id,
            capabilities=capabilities,
            context=[ContextMessage(role="user", content=prompt)],
            tools=tools,
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


def _offering_dicts_to_tool_definitions(
    offerings: list[dict], concrete_by_name: dict[str, ToolDefinition]
) -> list[ToolDefinition]:
    """Translates core.resolution.tool_offering_resolver's plain
    canonical dicts into Neptune's own ToolDefinition Pydantic model
    (A-008), expanding known catalog families into their real,
    ToolExecutor-routable definitions where one exists (B-011 -- see
    _CATALOG_TOOL_ID_TO_CONCRETE_NAMES). For a catalog tool_id with no
    known concrete backing yet, falls through to the original A-008
    behavior: `name` set to the offering's tool_id (the identifier
    ToolExecutor actually routes on), description built from the
    catalog's name/notes fields, empty parameters_schema. Nothing is
    silently dropped -- an offering that expands to nothing (empty
    concrete_by_name for a known family) or has no known family simply
    keeps its original degraded form, never disappears."""
    expanded: list[ToolDefinition] = []
    for offering in offerings:
        tool_id = offering["tool_id"]
        concrete_names = _CATALOG_TOOL_ID_TO_CONCRETE_NAMES.get(tool_id)
        if concrete_names:
            for name in concrete_names:
                concrete = concrete_by_name.get(name)
                if concrete is not None:
                    expanded.append(concrete)
            continue
        expanded.append(
            ToolDefinition(
                name=tool_id,
                description=f"{offering.get('name', tool_id)}: {offering.get('description', '')}".strip(
                    ": "
                ),
                parameters_schema={},
            )
        )
    return expanded
