"""Provider Adapter contract (PROVIDER_CONTRACT.md).

Purpose: "Represent an external or local provider behind a replaceable
adapter." Types here are the *internal* normalized boundary between
the Gateway/Router and a concrete adapter implementation -- still no
provider SDK types, but adapter-facing rather than agent-facing.

Invariants enforced:
  1. Provider adapters live at the edge (this module defines the edge
     shape; infrastructure/providers/* implements it).
  2. Provider failure degrades capability rather than corrupting core
     state (invoke() raises ProviderInvocationError, never a raw
     provider exception).
  3. Provider-specific SDKs must not leak into core interfaces (the
     Protocol below is the only surface a caller may depend on).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from neptune.core.contracts.model_gateway import (
    ContextMessage,
    ModelUsage,
    ToolDefinition,
    ToolIntent,
)
from neptune.core.domain import Capability, CostClass, ErrorType, HealthStatus


class ProviderRequest(BaseModel):
    """Normalized request handed to a single adapter, once the Router
    has already chosen a model_id/provider_id."""

    correlation_id: str
    model_id: str
    messages: list[ContextMessage]
    tools: list[ToolDefinition] = Field(default_factory=list)
    max_output_tokens: int | None = None


class ProviderResult(BaseModel):
    """Normalized adapter result. Distinct from ModelResult: this is
    what an adapter returns to the Gateway, before the Gateway attaches
    SelectedModelMetadata / routing rationale."""

    output_text: str | None = None
    tool_intents: list[ToolIntent] = Field(default_factory=list)
    usage: ModelUsage | None = None
    latency_ms: float | None = None
    finish_reason: str | None = None


class ProviderInvocationError(Exception):
    """Raised by an adapter's invoke(). Carries a normalized
    error_type so the Gateway/Router never needs to inspect a
    provider-specific exception (PROVIDER_CONTRACT invariant 3)."""

    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        retriable: bool,
        provider_id: str,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.retriable = retriable
        self.provider_id = provider_id


class ProviderHealth(BaseModel):
    """PROVIDER_CONTRACT responsibility: "expose health/availability
    information where possible"."""

    status: HealthStatus
    detail: str | None = None


@runtime_checkable
class ProviderAdapter(Protocol):
    """The only shape core/application code may depend on for a
    concrete provider. A conforming class needs no base class --
    Protocol conformance is structural (PEP 544)."""

    provider_id: str

    def capabilities(self) -> list[Capability]:
        """Declared capabilities this adapter can serve."""
        ...

    def cost_class(self) -> CostClass:
        """Declared cost tier, for budget-aware routing."""
        ...

    def health(self) -> ProviderHealth:
        """Best-effort health/availability signal."""
        ...

    def invoke(self, request: ProviderRequest) -> ProviderResult:
        """Execute one normalized request. Raises
        ProviderInvocationError on failure -- never a provider SDK
        exception."""
        ...
