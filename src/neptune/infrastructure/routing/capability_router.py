"""Default Router implementation.

This is deliberately simple: ROUTER_CONTRACT explicitly defers the
"exact scoring formula, weighting, health algorithm" to
implementation. This satisfies the contract's *responsibilities*
(capability match, availability, quota/cost, fallback, provider
independence, observability) without pretending to be a final
scoring policy.
"""

from __future__ import annotations

from neptune.core.contracts.model_gateway import BudgetEnvelope, RoutingConstraints
from neptune.core.contracts.router import (
    NoViableCandidateError,
    RouteDecision,
    RoutingCandidate,
)
from neptune.core.domain import Availability, Capability

_COST_ORDER = {"free": 0, "cheap": 1, "paid": 2, "frontier": 3}


class CapabilityRouter:
    """Filters candidates by capability + budget + constraints, then
    prefers: sticky provider (if still viable) > available health >
    lower cost class > declared quota remaining. Everything after the
    filter step becomes the fallback_chain, in the same preference
    order.
    """

    def select(
        self,
        correlation_id: str,
        requirements: list[Capability],
        candidates: list[RoutingCandidate],
        budget: BudgetEnvelope,
        routing_constraints: RoutingConstraints,
    ) -> RouteDecision:
        rejected: list[str] = []
        viable: list[RoutingCandidate] = []

        for c in candidates:
            if c.provider_id in routing_constraints.excluded_providers:
                rejected.append(f"{c.model_id}: excluded_provider")
                continue
            if c.availability != Availability.AVAILABLE:
                rejected.append(f"{c.model_id}: availability={c.availability.value}")
                continue
            if not set(requirements).issubset(set(c.capabilities)):
                missing = set(requirements) - set(c.capabilities)
                rejected.append(f"{c.model_id}: missing_capabilities={missing}")
                continue
            if _COST_ORDER[c.cost_class.value] > _COST_ORDER[budget.cost_class_max.value]:
                rejected.append(f"{c.model_id}: over_budget cost_class={c.cost_class.value}")
                continue
            viable.append(c)

        if not viable:
            raise NoViableCandidateError(
                f"no candidate satisfies requirements={requirements} "
                f"budget<={budget.cost_class_max.value}; rejected={rejected}"
            )

        def sort_key(c: RoutingCandidate) -> tuple:
            sticky = 0 if c.provider_id == routing_constraints.sticky_provider else 1
            preferred = 0 if c.provider_id in routing_constraints.preferred_providers else 1
            cost = _COST_ORDER[c.cost_class.value]
            quota = -(c.quota_remaining or 0.0)
            return (sticky, preferred, cost, quota)

        viable.sort(key=sort_key)
        selected, *fallback_chain = viable

        rationale = (
            f"selected {selected.model_id} ({selected.provider_id}): "
            f"matched capabilities={requirements}, cost_class="
            f"{selected.cost_class.value} <= budget "
            f"{budget.cost_class_max.value}; "
            f"{len(fallback_chain)} fallback(s) available; "
            f"{len(rejected)} candidate(s) rejected"
        )

        return RouteDecision(
            correlation_id=correlation_id,
            selected=selected,
            fallback_chain=fallback_chain,
            rejected=rejected,
            rationale=rationale,
        )
