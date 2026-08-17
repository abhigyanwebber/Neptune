"""Model Gateway contract (MODEL_CONTRACT.md).

Purpose (from the contract): "Provide a provider-neutral inference
boundary." Everything in this module is provider-neutral by
construction -- no field here may hold a provider SDK type, and no
provider/model *name* may be required to build a valid ModelRequest
(ADR-024 / ADR-004: capability pinning).

Invariants enforced by these shapes:
  1. Core agents do not require a specific provider SDK.
  2. Model identity is registry/resource metadata (SelectedModel is an
     *output*, never a required input field).
  3. Durable agent state is not provider-owned (ModelRequest carries
     identifiers only -- task_id/session_id/turn_id -- never provider
     conversation state).
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from neptune.core.domain import Capability, CostClass, ErrorType


class ContextMessage(BaseModel):
    """One bounded unit of assembled context (CONTEXT_CONTRACT output).

    The Gateway does not assemble context -- it only carries the
    bundle the Context Manager already produced.
    """

    role: str = Field(description='e.g. "system", "user", "assistant", "tool"')
    content: str
    name: str | None = None


class ToolDefinition(BaseModel):
    """A tool made available to the model for this turn only.

    Availability here is a capability declaration, not a grant of
    permission (TOOL_CONTRACT / PERMISSION_CONTRACT invariant:
    "tool availability does not grant permission").
    """

    name: str
    description: str
    parameters_schema: dict = Field(default_factory=dict)


class BudgetEnvelope(BaseModel):
    """Cost/size ceiling for this request (Reference Interfaces:
    "budget envelope")."""

    cost_class_max: CostClass = CostClass.FREE
    max_output_tokens: int | None = None
    max_total_tokens: int | None = None


class RoutingConstraints(BaseModel):
    """Optional hints to the Router. These narrow candidate selection;
    they are never a hard-coded provider dependency (ROUTER_CONTRACT
    invariant 1)."""

    require_tool_calling: bool = False
    require_structured_output: bool = False
    excluded_providers: list[str] = Field(default_factory=list)
    preferred_providers: list[str] = Field(default_factory=list)
    sticky_provider: str | None = Field(
        default=None,
        description="Prior provider for this session, honored when "
        "healthy and in-budget (ROUTER_CONTRACT invariant 3: model "
        "switching should respect session/context/cache boundaries).",
    )


class ModelRequest(BaseModel):
    """Normalized inference request. Matches Reference Interfaces:
    "infer(request: ModelRequest) -> ModelResult | ModelError"."""

    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    session_id: str
    turn_id: str
    capabilities: list[Capability] = Field(min_length=1)
    context: list[ContextMessage] = Field(default_factory=list)
    tools: list[ToolDefinition] = Field(default_factory=list)
    budget: BudgetEnvelope = Field(default_factory=BudgetEnvelope)
    routing_constraints: RoutingConstraints = Field(
        default_factory=RoutingConstraints
    )
    metadata: dict = Field(default_factory=dict)


class ToolIntent(BaseModel):
    """A model-emitted request to call a tool. Execution itself is out
    of scope (MODEL_CONTRACT non-responsibility: "tool execution")."""

    call_id: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class ModelUsage(BaseModel):
    """Usage metadata, when available (MODEL_CONTRACT responsibility:
    "report usage information when available")."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_estimate_usd: float | None = None


class SelectedModelMetadata(BaseModel):
    """Which registry entry served the request. This is the *only*
    place a model/provider identifier is allowed to surface to the
    caller, and it is metadata, not a dependency (ADR-024)."""

    model_id: str
    provider_id: str
    capabilities_matched: list[Capability]


class ModelResult(BaseModel):
    """Normalized inference result."""

    correlation_id: str
    output_text: str | None = None
    tool_intents: list[ToolIntent] = Field(default_factory=list)
    selected_model: SelectedModelMetadata
    usage: ModelUsage | None = None
    latency_ms: float | None = None
    finish_reason: str | None = None


class ModelError(BaseModel):
    """Normalized inference failure. No provider-specific exception
    type or payload may appear here (PROVIDER_CONTRACT invariant 3)."""

    correlation_id: str
    error_type: ErrorType
    message: str
    retriable: bool
    provider_id: str | None = None


class ModelGatewayError(Exception):
    """Raised by a ModelGateway implementation; carries a ModelError so
    callers can choose to catch-and-inspect or let it propagate."""

    def __init__(self, error: ModelError) -> None:
        super().__init__(error.message)
        self.error = error


@runtime_checkable
class ModelGateway(Protocol):
    """`infer(request: ModelRequest) -> ModelResult | ModelError`
    (REFERENCE_INTERFACES.md). Raises ModelGatewayError on failure
    rather than returning a union, to keep the happy path unwrapped;
    both are acceptable per REFERENCE_INTERFACES' "exact syntax may
    vary" note.
    """

    def infer(self, request: ModelRequest) -> ModelResult:
        ...
