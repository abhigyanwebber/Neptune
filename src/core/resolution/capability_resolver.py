"""Capability lookup: given a capability id, find eligible providers/tools.

Deliberately tolerant of capability ids that were never formally
registered in CapabilityRegistry (e.g. an example like "chat" that isn't
in A-003's fixed vocabulary) -- eligibility is determined entirely by
whether a Provider/ToolDefinition *declares* that capability in its own
`capabilities`/`capability` field, via the registries' existing
find_by_capability() lookups (already built in A-003). This resolver adds
no new registry logic; it's a thin, named facade so ProviderResolver and
callers don't reach into ProviderRegistry/ToolRegistry directly.
"""
from __future__ import annotations

from typing import Optional

from core.registry.capability_registry import Capability, CapabilityRegistry
from core.registry.provider_registry import Provider, ProviderRegistry
from core.registry.tool_registry import ToolDefinition, ToolRegistry


class CapabilityResolver:
    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        provider_registry: ProviderRegistry,
        tool_registry: ToolRegistry,
    ) -> None:
        self._capabilities = capability_registry
        self._providers = provider_registry
        self._tools = tool_registry

    def eligible_providers(self, capability_id: str) -> list[Provider]:
        return self._providers.find_by_capability(capability_id)

    def eligible_tools(self, capability_id: str) -> list[ToolDefinition]:
        return self._tools.find_by_capability(capability_id)

    def capability_metadata(self, capability_id: str) -> Optional[Capability]:
        """Returns the formal Capability record if one was registered, or
        None -- absence is not an error, since eligibility lookup above
        works regardless of whether the capability was formally
        registered."""
        return self._capabilities.get(capability_id)
