"""Resource dependency expansion.

Reuses core.registry.dependency_resolution.resolve_dependencies (A-003)
unchanged -- this module's only job is building the id -> depends_on map
that function needs, merged across all four registries, since a
Provider's depends_on can reference a Resource id, a Resource can depend
on another Resource, and (less commonly) a Tool's depends_on can too. No
new dependency-graph algorithm is introduced here.
"""
from __future__ import annotations

from typing import Optional

from core.registry.capability_registry import CapabilityRegistry
from core.registry.dependency_resolution import resolve_dependencies
from core.registry.provider_registry import ProviderRegistry
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry


class ResourceResolver:
    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        provider_registry: ProviderRegistry,
        resource_registry: ResourceRegistry,
        tool_registry: ToolRegistry,
    ) -> None:
        self._capabilities = capability_registry
        self._providers = provider_registry
        self._resources = resource_registry
        self._tools = tool_registry

    def expand_dependencies(self, entry_id: str, depends_on: Optional[list[str]] = None) -> list[str]:
        """Resolve the full dependency chain for `entry_id` (deepest
        dependency first, entry_id last).

        `depends_on` lets a caller resolve dependencies for an entry that
        isn't itself persisted in any registry (e.g. a Provider object a
        caller is evaluating before registering it) by supplying its
        direct dependency ids explicitly; if omitted, the entry must
        already exist in one of the four registries.

        Raises core.registry.dependency_resolution.UnresolvedDependencyError
        if a dependency (direct or transitive) doesn't exist in any
        registry, and DependencyCycleError if the dependency graph has a
        cycle -- both reused unchanged from A-003.
        """
        dependency_map = self._build_dependency_map()
        if entry_id not in dependency_map:
            dependency_map[entry_id] = list(depends_on or [])
        elif depends_on is not None:
            dependency_map[entry_id] = list(depends_on)
        return resolve_dependencies(entry_id, dependency_map)

    def _build_dependency_map(self) -> dict[str, list[str]]:
        dependency_map: dict[str, list[str]] = {}
        for capability in self._capabilities.list_all():
            dependency_map[capability.capability_id] = []
        for provider in self._providers.list_all():
            dependency_map[provider.provider_id] = list(provider.depends_on)
        for resource in self._resources.list_all():
            dependency_map[resource.resource_id] = list(resource.depends_on)
        for tool in self._tools.list_all():
            dependency_map[tool.tool_id] = list(tool.depends_on)
        return dependency_map
