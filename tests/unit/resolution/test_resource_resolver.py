import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import CapabilityRegistry
from core.registry.dependency_resolution import DependencyCycleError, UnresolvedDependencyError
from core.registry.provider_registry import Provider, ProviderRegistry
from core.registry.resource_registry import Resource, ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from core.resolution.resource_resolver import ResourceResolver
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)


@pytest.fixture()
def registries():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return (
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf)),
        ProviderRegistry(SqlAlchemyProviderRepository(sf)),
        ResourceRegistry(SqlAlchemyResourceRepository(sf)),
        ToolRegistry(SqlAlchemyToolDefinitionRepository(sf)),
        sf,
    )


def test_expand_dependencies_simple_chain(registries):
    capabilities, providers, resources, tools, _sf = registries
    resources.register(Resource(resource_id="docker", name="Docker"))
    resources.register(Resource(resource_id="local_fs", name="Local FS"))
    providers.register(Provider(provider_id="ollama", name="Ollama", depends_on=["local_fs"]))

    resolver = ResourceResolver(capabilities, providers, resources, tools)
    order = resolver.expand_dependencies("ollama")

    assert order == ["local_fs", "ollama"]


def test_expand_dependencies_transitive_through_resources(registries):
    capabilities, providers, resources, tools, _sf = registries
    resources.register(Resource(resource_id="docker", name="Docker"))
    resources.register(Resource(resource_id="postgres", name="Postgres", depends_on=["docker"]))
    providers.register(Provider(provider_id="groq", name="Groq", depends_on=["postgres"]))

    resolver = ResourceResolver(capabilities, providers, resources, tools)
    order = resolver.expand_dependencies("groq")

    assert order == ["docker", "postgres", "groq"]


def test_expand_dependencies_with_no_dependencies(registries):
    capabilities, providers, resources, tools, _sf = registries
    providers.register(Provider(provider_id="groq", name="Groq", depends_on=[]))

    resolver = ResourceResolver(capabilities, providers, resources, tools)
    assert resolver.expand_dependencies("groq") == ["groq"]


def test_expand_dependencies_for_unpersisted_entry_using_explicit_depends_on(registries):
    capabilities, providers, resources, tools, _sf = registries
    resources.register(Resource(resource_id="docker", name="Docker"))

    resolver = ResourceResolver(capabilities, providers, resources, tools)
    # "candidate-provider" isn't registered anywhere -- explicit depends_on
    # lets a caller resolve dependencies before committing to registration.
    order = resolver.expand_dependencies("candidate-provider", depends_on=["docker"])
    assert order == ["docker", "candidate-provider"]


def test_unresolved_dependency_raises(registries):
    capabilities, providers, resources, tools, _sf = registries
    providers.register(Provider(provider_id="groq", name="Groq", depends_on=["nonexistent_resource"]))

    resolver = ResourceResolver(capabilities, providers, resources, tools)
    with pytest.raises(UnresolvedDependencyError):
        resolver.expand_dependencies("groq")


def test_dependency_cycle_raises(registries):
    capabilities, providers, resources, tools, sf = registries
    # "a"/"b" aren't in the fixed resource vocabulary -- a fresh
    # non-strict registry (sharing the same underlying sqlite db via sf)
    # is used here since this test only cares about cycle detection, not
    # vocabulary validation (already covered by registry tests in A-003).
    nonstrict_resources = ResourceRegistry(SqlAlchemyResourceRepository(sf), strict=False)
    nonstrict_resources.register(Resource(resource_id="a", name="A", depends_on=["b"]))
    nonstrict_resources.register(Resource(resource_id="b", name="B", depends_on=["a"]))

    resolver = ResourceResolver(capabilities, providers, nonstrict_resources, tools)
    with pytest.raises(DependencyCycleError):
        resolver.expand_dependencies("a")
