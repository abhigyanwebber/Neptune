"""Provider selection: given a capability, pick the "best matching"
registered provider and expand its resource dependencies.

Selection policy (see 05_DECISIONS/ADR-039 for full rationale): rank
eligible providers by reliability status (STRUCTURAL best, RETIRED
excluded entirely), then verification_status (verified best), then
provider_id alphabetically as a final deterministic tiebreak. No provider
name is ever special-cased -- the ranking only reads fields every
Provider record has, so it works identically for any provider a future
Claude B registers, not just the five seeded in A-004.
"""
from __future__ import annotations

from typing import Optional

from core.registry.provider_registry import Provider, ProviderRegistry

from .capability_resolver import CapabilityResolver
from .models import ResolutionResult
from .resource_resolver import ResourceResolver

# Lower rank = more preferred. Anything not in this map (including a
# vocabulary the director expands later) sorts after every known status
# rather than raising, so resolution degrades gracefully instead of
# breaking on an unrecognized status string.
_STATUS_RANK: dict[str, int] = {"STRUCTURAL": 0, "BONUS": 1, "BURST": 2, "LOCAL": 3, "RETIRED": 99}
_VERIFICATION_RANK: dict[Optional[str], int] = {"verified": 0, "candidate": 1, "unverified": 2}


class ProviderResolver:
    def __init__(
        self,
        capability_resolver: CapabilityResolver,
        resource_resolver: ResourceResolver,
        provider_registry: ProviderRegistry,
    ) -> None:
        self._capability_resolver = capability_resolver
        self._resource_resolver = resource_resolver
        self._providers = provider_registry

    def resolve_provider(self, capability_id: str) -> ResolutionResult:
        eligible = [
            p
            for p in self._capability_resolver.eligible_providers(capability_id)
            if p.status != "RETIRED"
        ]

        if not eligible:
            return ResolutionResult(
                capability=capability_id,
                provider=None,
                dependencies=[],
                metadata={"eligible_provider_ids": [], "reason": "no eligible provider"},
            )

        ranked = sorted(eligible, key=self._rank_key)
        selected = ranked[0]

        dependencies = self._resource_resolver.expand_dependencies(
            selected.provider_id, selected.depends_on
        )

        return ResolutionResult(
            capability=capability_id,
            provider=selected,
            dependencies=dependencies,
            metadata={
                "eligible_provider_ids": [p.provider_id for p in eligible],
                "selection_reason": (
                    f"status={selected.status}, verification_status={selected.verification_status}"
                ),
            },
        )

    @staticmethod
    def _rank_key(provider: Provider) -> tuple[int, int, str]:
        return (
            _STATUS_RANK.get(provider.status, 50),
            _VERIFICATION_RANK.get(provider.verification_status, 50),
            provider.provider_id,
        )
