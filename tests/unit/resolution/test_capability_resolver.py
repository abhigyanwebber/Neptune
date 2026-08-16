import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import Capability, CapabilityRegistry
from core.registry.provider_registry import Provider, ProviderRegistry
from core.registry.tool_registry import ToolDefinition, ToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyToolDefinitionRepository,
)


@pytest.fixture()
def resolver():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    capabilities = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    providers = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    tools = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))

    capabilities.register(Capability(capability_id="coding", name="Coding"))
    providers.register(Provider(provider_id="groq", name="Groq", capabilities=["coding", "reasoning"]))
    providers.register(Provider(provider_id="gemini", name="Gemini", capabilities=["vision"]))
    tools.register(ToolDefinition(tool_id="terminal", name="Terminal", capability="terminal"))

    return CapabilityResolver(capabilities, providers, tools)


def test_eligible_providers_returns_matching_providers_only(resolver):
    eligible = resolver.eligible_providers("coding")
    assert [p.provider_id for p in eligible] == ["groq"]


def test_eligible_providers_for_unregistered_capability_returns_empty(resolver):
    # "chat" was never registered in CapabilityRegistry and no provider
    # declares it -- eligibility lookup must not raise, just return [].
    assert resolver.eligible_providers("chat") == []


def test_eligible_tools_returns_matching_tools(resolver):
    eligible = resolver.eligible_tools("terminal")
    assert [t.tool_id for t in eligible] == ["terminal"]


def test_capability_metadata_present_when_registered(resolver):
    meta = resolver.capability_metadata("coding")
    assert meta is not None
    assert meta.name == "Coding"


def test_capability_metadata_none_when_not_registered(resolver):
    assert resolver.capability_metadata("chat") is None
