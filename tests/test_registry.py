"""Registry schema-compliance tests.

Validates that config/registries/*.yaml conform to the required
fields declared in MODEL_REGISTRY.md / PROVIDER_REGISTRY.md, and that
the registry produces usable RoutingCandidates for the Router.
"""

from __future__ import annotations

from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Capability
from neptune.infrastructure.models.registry import ModelRegistry
from neptune.infrastructure.routing.capability_router import CapabilityRouter


def test_registry_loads_without_error(model_registry: ModelRegistry) -> None:
    assert "groq-llama-3.3-70b-versatile" in model_registry.models
    assert "groq" in model_registry.providers


def test_model_record_has_required_fields(model_registry: ModelRegistry) -> None:
    record = model_registry.models["groq-llama-3.3-70b-versatile"]
    assert record.verified_at
    assert record.tool_calling is True
    assert Capability.TOOL_USE in record.capabilities


def test_candidates_for_produces_routing_candidates(model_registry: ModelRegistry) -> None:
    candidates = model_registry.candidates_for([Capability.FAST_GENERAL])
    assert len(candidates) == 1
    assert isinstance(candidates[0], RoutingCandidate)
    assert candidates[0].provider_id == "groq"


def test_router_can_select_from_real_registry_data(
    model_registry: ModelRegistry, capability_router: CapabilityRouter
) -> None:
    from neptune.core.contracts.model_gateway import BudgetEnvelope, RoutingConstraints

    candidates = model_registry.candidates_for([Capability.TOOL_USE])
    decision = capability_router.select(
        correlation_id="corr-1",
        requirements=[Capability.TOOL_USE],
        candidates=candidates,
        budget=BudgetEnvelope(),
        routing_constraints=RoutingConstraints(),
    )
    assert decision.selected.model_id == "groq-llama-3.3-70b-versatile"
