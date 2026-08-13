"""Provider catalog.

Fixed vocabulary per director's brief: groq, openrouter, gemini, openai,
cerebras, mistral. `status` uses the reliability categories already defined
in 06_REGISTRIES/PROVIDER_REGISTRY.md (STRUCTURAL/BONUS/BURST/LOCAL/RETIRED)
so this registry is consistent with the Bible's existing vocabulary rather
than inventing a new one.

This is a catalog record only -- no provider SDK, no execution, no
authentication (PROVIDER_CONTRACT.md invariant: "Provider-specific SDKs
must not leak into core interfaces").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from core.contracts.registry import ProviderRepository

KNOWN_PROVIDERS: frozenset[str] = frozenset(
    {"groq", "openrouter", "gemini", "openai", "cerebras", "mistral"}
)

RELIABILITY_CATEGORIES: frozenset[str] = frozenset(
    {"STRUCTURAL", "BONUS", "BURST", "LOCAL", "RETIRED"}
)


class UnknownProviderError(ValueError):
    pass


@dataclass
class Provider:
    provider_id: str
    name: str
    provider_type: str = "model_provider"
    capabilities: list[str] = field(default_factory=list)
    status: str = "STRUCTURAL"
    depends_on: list[str] = field(default_factory=list)
    verification_date: Optional[str] = None
    notes: Optional[str] = None


class ProviderRegistry:
    def __init__(self, repository: "ProviderRepository", strict: bool = True) -> None:
        self._repo = repository
        self._strict = strict

    def register(self, provider: Provider) -> None:
        if self._strict and provider.provider_id not in KNOWN_PROVIDERS:
            raise UnknownProviderError(
                f"'{provider.provider_id}' is not in the known provider vocabulary: "
                f"{sorted(KNOWN_PROVIDERS)}"
            )
        self._repo.create(provider)

    def get(self, provider_id: str) -> Optional[Provider]:
        return self._repo.get(provider_id)

    def update(self, provider: Provider) -> None:
        self._repo.update(provider)

    def delete(self, provider_id: str) -> None:
        self._repo.delete(provider_id)

    def list_all(self) -> list[Provider]:
        return self._repo.list_all()

    def find_by_capability(self, capability_id: str) -> list[Provider]:
        """Router Contract invariant: "Routing is capability-oriented, not
        hard-coded to one provider." This is the lookup that makes that
        possible."""
        return [p for p in self._repo.list_all() if capability_id in p.capabilities]
