"""Cross-registry dependency resolution.

A Provider/Resource/Tool may declare `depends_on: list[str]` referencing
entries in any of the four registries (e.g. a `browser` tool might depend
on a `docker` resource; a provider might depend on nothing). This module
resolves a dependency chain into a safe installation/activation order
using plain topological sort -- no registry-specific knowledge, so it
works uniformly across all four catalogs.
"""
from __future__ import annotations


class DependencyCycleError(ValueError):
    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Dependency cycle detected: {' -> '.join(cycle)}")


class UnresolvedDependencyError(ValueError):
    def __init__(self, entry_id: str, missing: str) -> None:
        self.entry_id = entry_id
        self.missing = missing
        super().__init__(f"'{entry_id}' depends on unknown entry '{missing}'")


def resolve_dependencies(
    entry_id: str, depends_on_map: dict[str, list[str]], require_known: bool = True
) -> list[str]:
    """Return dependencies of `entry_id` in resolution order (deepest
    dependency first, `entry_id` itself last).

    `depends_on_map` maps every known entry id -> its direct dependency
    ids, merged across whichever registries are relevant to the caller.
    """
    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise DependencyCycleError(path[path.index(node):] + [node])
        if node not in depends_on_map:
            if require_known:
                parent = path[-1] if path else entry_id
                raise UnresolvedDependencyError(parent, node)
            visited.add(node)
            order.append(node)
            return

        visiting.add(node)
        path.append(node)
        for dep in depends_on_map[node]:
            visit(dep)
        path.pop()
        visiting.discard(node)
        visited.add(node)
        order.append(node)

    if entry_id not in depends_on_map:
        raise UnresolvedDependencyError(entry_id, entry_id)
    visit(entry_id)
    return order
