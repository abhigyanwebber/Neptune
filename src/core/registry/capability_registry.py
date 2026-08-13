"""Capability catalog: the fixed vocabulary a Router (future stage) uses to
match Task/Turn requirements against Providers and Tools that declare they
support a given capability.

Fixed vocabulary per director's brief for this task. Kept as a plain
frozenset rather than a Python Enum so the registry can still *store* an
unrecognized capability as data (useful for forward-compatibility / B's
work) while CapabilityRegistry.register() rejects anything outside the
known set by default -- see `strict` parameter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - avoids a runtime import cycle with
    # core.contracts.registry, which itself imports Capability from here.
    from core.contracts.registry import CapabilityRepository

KNOWN_CAPABILITIES: frozenset[str] = frozenset(
    {
        "reasoning",
        "coding",
        "web_search",
        "vision",
        "tool_use",
        "mcp",
        "browser",
        "terminal",
        "memory",
        "planning",
    }
)


class UnknownCapabilityError(ValueError):
    pass


@dataclass
class Capability:
    capability_id: str
    name: str
    description: Optional[str] = None


class CapabilityRegistry:
    """Thin domain service over a CapabilityRepository. Contains no
    persistence/provider logic of its own -- validation and lookup only."""

    def __init__(self, repository: "CapabilityRepository", strict: bool = True) -> None:
        self._repo = repository
        self._strict = strict

    def register(self, capability: Capability) -> None:
        if self._strict and capability.capability_id not in KNOWN_CAPABILITIES:
            raise UnknownCapabilityError(
                f"'{capability.capability_id}' is not in the known capability vocabulary: "
                f"{sorted(KNOWN_CAPABILITIES)}"
            )
        self._repo.create(capability)

    def get(self, capability_id: str) -> Optional[Capability]:
        return self._repo.get(capability_id)

    def update(self, capability: Capability) -> None:
        self._repo.update(capability)

    def delete(self, capability_id: str) -> None:
        self._repo.delete(capability_id)

    def list_all(self) -> list[Capability]:
        return self._repo.list_all()
