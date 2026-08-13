"""Router contract (ROUTER_CONTRACT.md).

Purpose: "Select an appropriate model/provider for a model request."

Invariants enforced:
  1. Routing is capability-oriented, not hard-coded to one provider
     (select() takes a list of RoutingCandidate, never a provider name).
  2. A failed provider must have a defined degradation/fallback path
     where alternatives exist (RouteDecision.fallback_chain).
  3. Model switching should respect session/context/cache boundaries
     (RoutingConstraints.sticky_provider, honored by implementations).

Deferred by the contract (left to infrastructure/routing/*, not
fixed here): exact scoring formula, weighting, health algorithm,
cache-cost model, final fallback policy.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from neptune.core.contracts.model_gateway import BudgetEnvelope, RoutingConstraints
from neptune.core.domain import Availability, Capability, CostClass


class RoutingCandidate(BaseModel):
    """One registry-derived option the Router may choose. Built by the
    caller (application/gateway_service.py) from the model/provider
    registries -- the Router itself never touches storage."""

    model_id: str
    provider_id: str
    capabilities: list[Capability]
    cost_class: CostClass
    availability: Availability
    quota_remaining: float | None = Field(
        default=None, description="0-1 fraction if known, else None"
    )


class RouteDecision(BaseModel):
    """The Router's output, including enough detail for observability
    (ROUTER_CONTRACT responsibility: "expose the selection decision
    for observability")."""

    correlation_id: str
    selected: RoutingCandidate
    fallback_chain: list[RoutingCandidate] = Field(default_factory=list)
    rejected: list[str] = Field(
        default_factory=list,
        description="model_id: reason, human-readable, for observability",
    )
    rationale: str


class NoViableCandidateError(Exception):
    """Raised when no candidate satisfies the requirements/budget."""


@runtime_checkable
class Router(Protocol):
    """`select(...) -> RouteDecision` (REFERENCE_INTERFACES.md).
    Raises NoViableCandidateError when nothing satisfies the request
    rather than returning an empty/sentinel decision.
    """

    def select(
        self,
        correlation_id: str,
        requirements: list[Capability],
        candidates: list[RoutingCandidate],
        budget: BudgetEnvelope,
        routing_constraints: RoutingConstraints,
    ) -> RouteDecision:
        ...
