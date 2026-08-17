import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import Capability, CapabilityRegistry, UnknownCapabilityError
from core.registry.provider_registry import Provider, ProviderRegistry, UnknownProviderError
from core.registry.resource_registry import Resource, ResourceRegistry, UnknownResourceError
from core.registry.tool_registry import ToolDefinition, ToolRegistry, UnknownToolError
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    return make_session_factory(engine)


# ---------------------------------------------------------------------------
# Capability Registry: CRUD + vocabulary validation
# ---------------------------------------------------------------------------

def test_capability_registry_crud(session_factory):
    registry = CapabilityRegistry(SqlAlchemyCapabilityRepository(session_factory))
    registry.register(Capability(capability_id="coding", name="Coding"))

    fetched = registry.get("coding")
    assert fetched.name == "Coding"

    fetched.name = "Software Coding"
    registry.update(fetched)
    assert registry.get("coding").name == "Software Coding"

    assert {c.capability_id for c in registry.list_all()} == {"coding"}

    registry.delete("coding")
    assert registry.get("coding") is None


def test_capability_registry_rejects_unknown_capability(session_factory):
    registry = CapabilityRegistry(SqlAlchemyCapabilityRepository(session_factory))
    with pytest.raises(UnknownCapabilityError):
        registry.register(Capability(capability_id="telepathy", name="Telepathy"))


def test_capability_registry_non_strict_allows_forward_compat(session_factory):
    registry = CapabilityRegistry(SqlAlchemyCapabilityRepository(session_factory), strict=False)
    registry.register(Capability(capability_id="future_capability", name="Future"))
    assert registry.get("future_capability") is not None


# ---------------------------------------------------------------------------
# Provider Registry: CRUD + capability lookup
# ---------------------------------------------------------------------------

def test_provider_registry_crud_and_capability_lookup(session_factory):
    registry = ProviderRegistry(SqlAlchemyProviderRepository(session_factory))
    registry.register(
        Provider(provider_id="groq", name="Groq", capabilities=["reasoning", "coding"])
    )
    registry.register(
        Provider(provider_id="gemini", name="Gemini", capabilities=["vision", "coding"])
    )
    registry.register(Provider(provider_id="mistral", name="Mistral", capabilities=["reasoning"]))

    assert registry.get("groq").name == "Groq"
    assert {p.provider_id for p in registry.list_all()} == {"groq", "gemini", "mistral"}

    coding_providers = {p.provider_id for p in registry.find_by_capability("coding")}
    assert coding_providers == {"groq", "gemini"}

    registry.delete("mistral")
    assert registry.get("mistral") is None


def test_provider_registry_rejects_unknown_provider(session_factory):
    registry = ProviderRegistry(SqlAlchemyProviderRepository(session_factory))
    with pytest.raises(UnknownProviderError):
        registry.register(Provider(provider_id="totally-made-up", name="Nope"))


# ---------------------------------------------------------------------------
# Resource Registry: CRUD + status lookup
# ---------------------------------------------------------------------------

def test_resource_registry_crud_and_status_lookup(session_factory):
    registry = ResourceRegistry(SqlAlchemyResourceRepository(session_factory))
    registry.register(Resource(resource_id="postgres", name="Postgres", status="ACTIVE"))
    registry.register(Resource(resource_id="docker", name="Docker", status="ACTIVE"))
    registry.register(Resource(resource_id="cloudflare", name="Cloudflare", status="DORMANT"))

    active = {r.resource_id for r in registry.find_by_status("ACTIVE")}
    assert active == {"postgres", "docker"}

    resource = registry.get("cloudflare")
    resource.status = "ACTIVE"
    registry.update(resource)
    assert registry.get("cloudflare").status == "ACTIVE"


def test_resource_registry_rejects_unknown_resource(session_factory):
    registry = ResourceRegistry(SqlAlchemyResourceRepository(session_factory))
    with pytest.raises(UnknownResourceError):
        registry.register(Resource(resource_id="aws-lambda", name="AWS Lambda"))


# ---------------------------------------------------------------------------
# Tool Registry: CRUD + capability lookup
# ---------------------------------------------------------------------------

def test_tool_registry_crud_and_capability_lookup(session_factory):
    registry = ToolRegistry(SqlAlchemyToolDefinitionRepository(session_factory))
    registry.register(ToolDefinition(tool_id="browser", name="Browser", capability="browser"))
    registry.register(ToolDefinition(tool_id="terminal", name="Terminal", capability="terminal"))

    assert registry.get("browser").capability == "browser"
    assert [t.tool_id for t in registry.find_by_capability("terminal")] == ["terminal"]


def test_tool_registry_rejects_unknown_tool(session_factory):
    registry = ToolRegistry(SqlAlchemyToolDefinitionRepository(session_factory))
    with pytest.raises(UnknownToolError):
        registry.register(ToolDefinition(tool_id="teleporter", name="Teleporter"))
