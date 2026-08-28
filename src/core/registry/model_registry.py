"""Model catalog.

Per task C-004: represents the concepts B-003's live validation and B-001's
ModelRegistry established as necessary -- model identifier, provider
relationship, verification metadata, operational status, and the
provider-facing model name -- in the canonical (Postgres-backed) registry
system, so a future ModelGateway integration does not depend on the
deprecated YAML registry (src/neptune/infrastructure/models/registry.py).

Unlike Capability/Provider/Resource/Tool (A-003), there is no fixed,
enumerable vocabulary of model ids -- new models appear continuously and
are provider-published data, not a small closed set Neptune defines. So,
unlike those four registries, ModelRegistry.register() has no `strict`
vocabulary check at all; only the id-uniqueness the repository already
enforces (primary key) applies.

`model_id` (the registry's own key, e.g. "groq-llama-3.3-70b-versatile")
is kept deliberately distinct from `provider_model_name` (the string
actually sent to the provider's API, e.g. "llama-3.3-70b-versatile").
B-003's live Groq validation found a real bug from conflating these two
(the registry key was sent to the provider and rejected with a 404) --
this schema keeps that distinction structural rather than relying on
callers to remember it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .audit import emit_registry_event

if TYPE_CHECKING:  # pragma: no cover
    from core.contracts.registry import ModelRepository
    from core.contracts.repositories import EventRepository

# Mirrors neptune.core.domain.capability.Availability's values exactly
# (available/degraded/unavailable/retired) -- this is the literal existing
# contract concept for "operational status" the task points to (B-003
# evidence), not a newly invented vocabulary.
MODEL_STATUSES: frozenset[str] = frozenset({"available", "degraded", "unavailable", "retired"})


@dataclass
class Model:
    model_id: str
    provider_id: str
    provider_model_name: str
    capabilities: list[str] = field(default_factory=list)
    status: str = "available"
    depends_on: list[str] = field(default_factory=list)
    verification_date: Optional[str] = None
    notes: Optional[str] = None
    verification_source: Optional[str] = None
    verification_status: Optional[str] = None
    last_checked: Optional[str] = None


class ModelRegistry:
    def __init__(
        self,
        repository: "ModelRepository",
        event_repo: "Optional[EventRepository]" = None,
    ) -> None:
        self._repo = repository
        self._events = event_repo

    def register(self, model: Model) -> None:
        self._repo.create(model)
        emit_registry_event(self._events, "registry.model.registered", model.model_id)

    def get(self, model_id: str) -> Optional[Model]:
        return self._repo.get(model_id)

    def update(self, model: Model) -> None:
        self._repo.update(model)
        emit_registry_event(self._events, "registry.model.updated", model.model_id)

    def delete(self, model_id: str) -> None:
        self._repo.delete(model_id)
        emit_registry_event(self._events, "registry.model.deleted", model_id)

    def list_all(self) -> list[Model]:
        return self._repo.list_all()

    def list_for_provider(self, provider_id: str) -> list[Model]:
        return self._repo.list_for_provider(provider_id)

    def find_by_capability(self, capability_id: str) -> list[Model]:
        return [m for m in self._repo.list_all() if capability_id in m.capabilities]
