"""Canonical-registry-backed candidate source for ModelGatewayService.

Replaces the legacy YAML ModelRegistry.candidates_for() dependency
(B-001/B-003) identified by C-005's audit (DIRECTOR_LEGACY_REGISTRY_
AUDIT.md section 2) as the live path's SINGLE registry dependency
point. Reads from Claude A's canonical, Postgres-backed registry
(core.registry.model_registry.ModelRegistry + core.resolution.
provider_resolver.ProviderResolver) instead.

This module deliberately imports from src/core (Claude A's canonical
registry/resolution modules) -- that is the intended cross-lane read
for this specific adapter, exactly as ToolPortAdapter is the intended
cross-lane read for tool execution (B-006/ADR-044). No frozen contract
is touched; this is a new implementation-detail adapter, per B-008's
"prefer an adapter over changing Core" discipline. It lives entirely
on the infrastructure side (src/neptune/infrastructure), matching the
same boundary as GroqAdapter/ToolPortAdapter -- src/neptune/core never
imports this module or anything it depends on.
"""
from __future__ import annotations

from core.registry.capability_bridge import (
    RejectedExternalCapabilityError,
    UnknownExternalCapabilityError,
    translate_capabilities,
)
from core.registry.model_registry import Model as CanonicalModel
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
from core.resolution.provider_resolver import ProviderResolver

from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Availability, Capability, CostClass

_CANONICAL_STATUS_TO_AVAILABILITY: dict[str, Availability] = {
    "available": Availability.AVAILABLE,
    "degraded": Availability.DEGRADED,
    "unavailable": Availability.UNAVAILABLE,
    "retired": Availability.RETIRED,
}


def _capability_to_external(canonical_capability_id: str) -> Capability | None:
    """Reverse of capability_bridge.translate_capability(): canonical id
    -> external (neptune.core.domain.capability.Capability) enum member,
    or None if the canonical id has no external-side equivalent (e.g.
    "web_search", "mcp", "browser", "terminal", "memory" -- canonical-
    only capabilities per capability_bridge.py's own docstring). Safe
    because 8 of the 10 external values are documented to match a
    canonical id by exact string identity; this is not a guess.
    """
    try:
        return Capability(canonical_capability_id)
    except ValueError:
        return None


class CanonicalRegistryCandidateSource:
    """Structurally satisfies the same candidates_for() shape the legacy
    ModelRegistry provided to ModelGatewayService -- this class is the
    sole call-site swap C-005's audit identified as sufficient for
    cutover (DIRECTOR_LEGACY_REGISTRY_AUDIT.md section 2).

    Resolution scope (deliberately minimal, not a new routing
    algorithm): resolves eligible PROVIDERS via ProviderResolver
    against the first requested capability only -- "no speculative
    routing algorithms" (B-008 out-of-scope). ProviderResolver returns
    one top-ranked provider plus the full eligible set in
    `resolution.metadata["eligible_provider_ids"]`; this class collects
    models from EVERY eligible provider, not just the top-ranked one,
    because ProviderResolver's ranking has no concept of "which
    provider Neptune actually has a working ProviderAdapter for" (that
    is a ModelGatewayService/adapters-dict concern, one layer up) --
    e.g. it may rank Gemini above Groq for "coding" even though only
    Groq has models registered and an adapter wired in. Returning every
    eligible provider's models as candidates lets the existing,
    unmodified fallback mechanism already built in
    ModelGatewayService.infer() (B-001: `adapter = self._adapters.get(
    candidate.provider_id); if adapter is None: continue`) and
    CapabilityRouter's own fallback_chain (B-001) naturally skip
    providers with no adapter or no models, landing on whichever
    eligible provider Neptune can actually reach. This is not a new
    routing algorithm -- it reuses two already-existing, already-tested
    fallback mechanisms; it only changes what candidate list they see.
    CapabilityRouter still does its own full-set capability match
    against every requested capability, exactly as it already did
    against the legacy registry's candidates.
    """

    def __init__(
        self,
        provider_resolver: ProviderResolver,
        model_registry: CanonicalModelRegistry,
    ) -> None:
        self._provider_resolver = provider_resolver
        self._models = model_registry

    def candidates_for(self, capabilities: list[Capability]) -> list[RoutingCandidate]:
        if not capabilities:
            return []

        try:
            canonical_capability_id = translate_capabilities([capabilities[0].value])[0]
        except (UnknownExternalCapabilityError, RejectedExternalCapabilityError):
            return []

        resolution = self._provider_resolver.resolve_provider(canonical_capability_id)
        if resolution.provider is None:
            return []

        eligible_provider_ids = resolution.metadata.get("eligible_provider_ids") or [
            resolution.provider.provider_id
        ]

        candidates: list[RoutingCandidate] = []
        for provider_id in eligible_provider_ids:
            models = [
                m
                for m in self._models.list_for_provider(provider_id)
                if canonical_capability_id in m.capabilities
            ]
            candidates.extend(self._to_routing_candidate(m) for m in models)
        return candidates

    @staticmethod
    def _to_routing_candidate(m: CanonicalModel) -> RoutingCandidate:
        external_capabilities = [
            cap for cap in (_capability_to_external(c) for c in m.capabilities) if cap is not None
        ]
        return RoutingCandidate(
            # provider_model_name, NOT model_id -- preserves the B-003
            # bug fix (B-008 item 5): model_id is the registry's own
            # key ("groq-llama-3.3-70b-versatile"), provider_model_name
            # is what actually gets sent to the provider's API
            # ("llama-3.3-70b-versatile"). Sending the former caused a
            # real 404 in B-003; the canonical Model entity keeps this
            # distinction structural (see model_registry.py docstring).
            model_id=m.provider_model_name,
            provider_id=m.provider_id,
            capabilities=external_capabilities,
            # The canonical Model entity has no cost_class field yet
            # (C-004 scope; folded into `notes` instead -- see
            # 06_REGISTRIES/data/models.yaml's header comment). Known
            # limitation, not fabricated certainty: defaulting to FREE
            # is correct for the one seeded model (Groq's free tier)
            # but would need a real field before a second, paid model
            # is registered.
            cost_class=CostClass.FREE,
            availability=_CANONICAL_STATUS_TO_AVAILABILITY.get(m.status, Availability.UNAVAILABLE),
            quota_remaining=None,
        )
