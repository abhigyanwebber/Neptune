"""Resource catalog.

Fixed vocabulary per director's brief: github, postgres, supabase,
cloudflare, local_fs, docker. `status` uses the resource lifecycle states
already defined in 06_REGISTRIES/RESOURCE_REGISTRY.md, and `criticality`
uses that same document's R0-R3 classes, so this stays consistent with the
existing Bible vocabulary.

Catalog record only (RESOURCE_CONTRACT.md: "hard-coding provider APIs into
core" is a non-responsibility) -- no cloud SDK calls, no credential
handling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from core.contracts.registry import ResourceRepository

KNOWN_RESOURCES: frozenset[str] = frozenset(
    {"github", "postgres", "supabase", "cloudflare", "local_fs", "docker"}
)

RESOURCE_STATES: frozenset[str] = frozenset(
    {
        "DISCOVERED",
        "ELIGIBLE",
        "CLAIMED",
        "ACTIVE",
        "DORMANT",
        "EXPIRING",
        "EXPIRED",
        "REPLACED",
    }
)

CRITICALITY_CLASSES: frozenset[str] = frozenset({"R0", "R1", "R2", "R3"})


class UnknownResourceError(ValueError):
    pass


@dataclass
class Resource:
    resource_id: str
    name: str
    resource_type: str = "infrastructure"
    status: str = "DISCOVERED"
    criticality: str = "R1"
    depends_on: list[str] = field(default_factory=list)
    verification_date: Optional[str] = None
    notes: Optional[str] = None


class ResourceRegistry:
    def __init__(self, repository: "ResourceRepository", strict: bool = True) -> None:
        self._repo = repository
        self._strict = strict

    def register(self, resource: Resource) -> None:
        if self._strict and resource.resource_id not in KNOWN_RESOURCES:
            raise UnknownResourceError(
                f"'{resource.resource_id}' is not in the known resource vocabulary: "
                f"{sorted(KNOWN_RESOURCES)}"
            )
        self._repo.create(resource)

    def get(self, resource_id: str) -> Optional[Resource]:
        return self._repo.get(resource_id)

    def update(self, resource: Resource) -> None:
        self._repo.update(resource)

    def delete(self, resource_id: str) -> None:
        self._repo.delete(resource_id)

    def list_all(self) -> list[Resource]:
        return self._repo.list_all()

    def find_by_status(self, status: str) -> list[Resource]:
        return [r for r in self._repo.list_all() if r.status == status]
