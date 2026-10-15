"""Independent canonical-registry seeding for the live tests (A-010/A-011).

The live tests resolve a real model through the canonical registry
(providers, capabilities, resources, models), so that data must exist. They
previously assumed some earlier test had populated it, so they passed in
suite order and failed in isolation or on an empty database. This seeds the
shipped YAML itself, the same way the production composition root does
(neptune.application.composition.build_plan_runner), and is idempotent.
"""
from __future__ import annotations

from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.registry_loader import load_registry_directory
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyModelRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)
from neptune.application.composition import DEFAULT_REGISTRY_DIR


def seed_canonical_registry(session_factory) -> None:
    results = load_registry_directory(
        DEFAULT_REGISTRY_DIR,
        CapabilityRegistry(SqlAlchemyCapabilityRepository(session_factory)),
        ProviderRegistry(SqlAlchemyProviderRepository(session_factory)),
        ResourceRegistry(SqlAlchemyResourceRepository(session_factory)),
        ToolRegistry(SqlAlchemyToolDefinitionRepository(session_factory)),
        ModelRegistry(SqlAlchemyModelRepository(session_factory)),
    )
    errors = {name: r.errors for name, r in results.items() if r.errors}
    assert not errors, f"registry seed data failed to load: {errors}"
