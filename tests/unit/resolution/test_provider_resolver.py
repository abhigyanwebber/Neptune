import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import CapabilityRegistry
from core.registry.provider_registry import Provider, ProviderRegistry
from core.registry.resource_registry import Resource, ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.resource_resolver import ResourceResolver
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)


@pytest.fixture()
def setup():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    capabilities = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    providers = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    resources = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    tools = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))

    capability_resolver = CapabilityResolver(capabilities, providers, tools)
    resource_resolver = ResourceResolver(capabilities, providers, resources, tools)
    provider_resolver = ProviderResolver(capability_resolver, resource_resolver, providers)

    return providers, resources, provider_resolver


def test_resolve_provider_picks_structural_over_local(setup):
    providers, _resources, resolver = setup
    providers.register(
        Provider(provider_id="ollama", name="Ollama", capabilities=["reasoning"], status="LOCAL")
    )
    providers.register(
        Provider(
            provider_id="groq",
            name="Groq",
            capabilities=["reasoning"],
            status="STRUCTURAL",
            verification_status="verified",
        )
    )

    result = resolver.resolve_provider("reasoning")

    assert result.capability == "reasoning"
    assert result.provider.provider_id == "groq"
    assert set(result.metadata["eligible_provider_ids"]) == {"ollama", "groq"}


def test_resolve_provider_breaks_ties_alphabetically(setup):
    providers, _resources, resolver = setup
    for pid in ("openrouter", "groq", "gemini"):
        providers.register(
            Provider(
                provider_id=pid,
                name=pid,
                capabilities=["coding"],
                status="STRUCTURAL",
                verification_status="verified",
            )
        )

    result = resolver.resolve_provider("coding")
    # gemini < groq < openrouter alphabetically -- all else being equal.
    assert result.provider.provider_id == "gemini"


def test_resolve_provider_excludes_retired(setup):
    providers, _resources, resolver = setup
    providers.register(
        Provider(provider_id="mistral", name="Mistral", capabilities=["coding"], status="RETIRED")
    )

    result = resolver.resolve_provider("coding")
    assert result.provider is None
    assert result.metadata["eligible_provider_ids"] == []


def test_resolve_provider_no_eligible_provider_returns_none_gracefully(setup):
    _providers, _resources, resolver = setup
    result = resolver.resolve_provider("chat")  # never registered anywhere
    assert result.provider is None
    assert result.dependencies == []
    assert result.metadata["reason"] == "no eligible provider"


def test_resolve_provider_expands_dependencies(setup):
    providers, resources, resolver = setup
    resources.register(Resource(resource_id="local_fs", name="Local FS"))
    providers.register(
        Provider(
            provider_id="ollama",
            name="Ollama",
            capabilities=["reasoning"],
            status="LOCAL",
            depends_on=["local_fs"],
        )
    )

    result = resolver.resolve_provider("reasoning")

    assert result.provider.provider_id == "ollama"
    assert result.dependencies == ["local_fs", "ollama"]
