"""Model/provider registry.

Loads config/registries/*.yaml, validates required fields per
06_REGISTRIES/MODEL_REGISTRY.md and PROVIDER_REGISTRY.md, and exposes
RoutingCandidate objects for the Router. This is the only place in
the codebase that reads provider/model *names* from data instead of
code (ADR-024).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Availability, Capability, CostClass


class ModelRecord(BaseModel):
    """Mirrors the required-fields block in MODEL_REGISTRY.md."""

    id: str
    provider: str
    model: str
    capabilities: list[Capability]
    context_limit: int
    tool_calling: bool
    structured_output: bool
    cost_class: CostClass
    quota: str
    health: str
    availability: Availability
    verified_at: str
    fallbacks: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    notes: str = ""


class ProviderRecord(BaseModel):
    """Mirrors the required-fields block in PROVIDER_REGISTRY.md."""

    id: str
    name: str
    provider_type: str
    regions: list[str] = Field(default_factory=list)
    endpoints: list[str] = Field(default_factory=list)
    capabilities: list[Capability] = Field(default_factory=list)
    pricing_snapshot: str
    quota_snapshot: str
    health: str
    verification_date: str
    terms_url: str
    status: str
    failure_history: str = ""
    fallback_providers: list[str] = Field(default_factory=list)
    cache_characteristics: str = ""
    notes: str = ""


class ModelRegistry:
    """Loads and validates the model + provider registry YAML files."""

    def __init__(self, models: list[ModelRecord], providers: list[ProviderRecord]) -> None:
        self.models = {m.id: m for m in models}
        self.providers = {p.id: p for p in providers}

    @classmethod
    def load(cls, config_dir: Path) -> "ModelRegistry":
        model_data = yaml.safe_load((config_dir / "model_registry.yaml").read_text())
        provider_data = yaml.safe_load((config_dir / "provider_registry.yaml").read_text())
        models = [ModelRecord(**m) for m in (model_data or {}).get("models", [])]
        providers = [ProviderRecord(**p) for p in (provider_data or {}).get("providers", [])]
        return cls(models=models, providers=providers)

    def candidates_for(self, capabilities: list[Capability]) -> list[RoutingCandidate]:
        """All registered models, as RoutingCandidate. Filtering by
        the requested capabilities is the Router's job, not the
        registry's -- this just does the id -> RoutingCandidate shape
        translation and passes every entry through."""
        del capabilities  # selection happens in the Router, per ROUTER_CONTRACT
        return [
            RoutingCandidate(
                model_id=m.id,
                provider_id=m.provider,
                capabilities=m.capabilities,
                cost_class=m.cost_class,
                availability=m.availability,
                quota_remaining=None,
            )
            for m in self.models.values()
        ]
