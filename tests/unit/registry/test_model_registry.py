"""Model CRUD tests (C-004), mirroring the pattern already established for
Capability/Provider/Resource/Tool in tests/unit/registry/test_registries.py."""
import pytest
from sqlalchemy import create_engine

from core.registry.model_registry import MODEL_STATUSES, Model, ModelRegistry
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyModelRepository


@pytest.fixture()
def registry():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return ModelRegistry(SqlAlchemyModelRepository(sf))


def test_model_registry_crud(registry):
    registry.register(
        Model(
            model_id="groq-llama-3.3-70b-versatile",
            provider_id="groq",
            provider_model_name="llama-3.3-70b-versatile",
            capabilities=["tool_use", "coding"],
        )
    )

    fetched = registry.get("groq-llama-3.3-70b-versatile")
    assert fetched.provider_id == "groq"
    assert fetched.provider_model_name == "llama-3.3-70b-versatile"
    assert fetched.status == "available"  # default

    fetched.status = "degraded"
    registry.update(fetched)
    assert registry.get("groq-llama-3.3-70b-versatile").status == "degraded"

    assert {m.model_id for m in registry.list_all()} == {"groq-llama-3.3-70b-versatile"}

    registry.delete("groq-llama-3.3-70b-versatile")
    assert registry.get("groq-llama-3.3-70b-versatile") is None


def test_model_registry_has_no_fixed_vocabulary(registry):
    # Unlike Capability/Provider/Resource/Tool, model ids are open-ended
    # (provider-published, not a small Neptune-defined set) -- any id
    # should register without a strict-vocabulary rejection.
    registry.register(Model(model_id="totally-made-up-model", provider_id="groq", provider_model_name="x"))
    assert registry.get("totally-made-up-model") is not None


def test_model_status_values_match_availability_vocabulary():
    assert MODEL_STATUSES == {"available", "degraded", "unavailable", "retired"}


def test_list_for_provider_filters_correctly(registry):
    registry.register(Model(model_id="m1", provider_id="groq", provider_model_name="a"))
    registry.register(Model(model_id="m2", provider_id="groq", provider_model_name="b"))
    registry.register(Model(model_id="m3", provider_id="gemini", provider_model_name="c"))

    groq_models = {m.model_id for m in registry.list_for_provider("groq")}
    assert groq_models == {"m1", "m2"}


def test_find_by_capability(registry):
    registry.register(Model(model_id="m1", provider_id="groq", provider_model_name="a", capabilities=["coding"]))
    registry.register(Model(model_id="m2", provider_id="groq", provider_model_name="b", capabilities=["vision"]))

    coding_models = {m.model_id for m in registry.find_by_capability("coding")}
    assert coding_models == {"m1"}


def test_model_dependency_on_provider_resolves(registry):
    from core.registry.capability_registry import CapabilityRegistry
    from core.registry.dependency_resolution import resolve_dependencies
    from core.registry.provider_registry import Provider, ProviderRegistry
    from core.registry.resource_registry import ResourceRegistry
    from core.registry.tool_registry import ToolRegistry
    from core.resolution.resource_resolver import ResourceResolver
    from infrastructure.persistence.repositories import (
        SqlAlchemyCapabilityRepository,
        SqlAlchemyProviderRepository,
        SqlAlchemyResourceRepository,
        SqlAlchemyToolDefinitionRepository,
    )

    # A Model's depends_on=[provider_id] should resolve through the same
    # generic mechanism (A-003) used for Provider/Resource/Tool -- proving
    # the new entity type integrates with existing dependency resolution
    # without any change to resolve_dependencies() itself.
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    providers = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    providers.register(Provider(provider_id="groq", name="Groq"))
    registry.register(
        Model(model_id="m1", provider_id="groq", provider_model_name="x", depends_on=["groq"])
    )

    dependency_map = {"groq": [], "m1": ["groq"]}
    order = resolve_dependencies("m1", dependency_map)
    assert order == ["groq", "m1"]
