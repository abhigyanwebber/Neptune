"""C-004: Provider extended operational metadata, capability vocabulary
reconciliation, and compatibility with the existing Resolution layer
(A-006), following existing test conventions in this directory."""
import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import KNOWN_CAPABILITIES, Capability, CapabilityRegistry
from core.registry.provider_registry import Provider, ProviderRegistry
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.resource_resolver import ResourceResolver
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry


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
    )


# ---------------------------------------------------------------------------
# Provider extended metadata
# ---------------------------------------------------------------------------

def test_provider_extended_fields_round_trip(registries):
    _capabilities, providers, _resources, _tools = registries
    providers.register(
        Provider(
            provider_id="groq",
            name="Groq",
            regions=["us"],
            endpoints=["https://api.groq.com/openai/v1"],
            pricing_snapshot="Free tier, no card required",
            quota_snapshot="~30 req/min",
            health_snapshot="unknown",
            terms_url="https://groq.com/terms-of-use/",
            fallback_providers=["openrouter"],
        )
    )
    fetched = providers.get("groq")
    assert fetched.regions == ["us"]
    assert fetched.endpoints == ["https://api.groq.com/openai/v1"]
    assert fetched.pricing_snapshot == "Free tier, no card required"
    assert fetched.quota_snapshot == "~30 req/min"
    assert fetched.health_snapshot == "unknown"
    assert fetched.terms_url == "https://groq.com/terms-of-use/"
    assert fetched.fallback_providers == ["openrouter"]


def test_provider_extended_fields_default_empty(registries):
    # Backward compatibility: existing callers that don't pass the new
    # fields (e.g. all of A-003/A-004's original test code) must be
    # unaffected.
    _capabilities, providers, _resources, _tools = registries
    providers.register(Provider(provider_id="groq", name="Groq"))
    fetched = providers.get("groq")
    assert fetched.regions == []
    assert fetched.endpoints == []
    assert fetched.pricing_snapshot is None
    assert fetched.fallback_providers == []


def test_fallback_providers_distinct_from_depends_on(registries):
    # ADR-042: fallback_providers is NOT a dependency-resolution input --
    # it must not appear in a depends_on-based dependency graph.
    from core.registry.dependency_resolution import resolve_dependencies

    _capabilities, providers, _resources, _tools = registries
    providers.register(
        Provider(provider_id="groq", name="Groq", depends_on=[], fallback_providers=["openrouter"])
    )
    dependency_map = {"groq": []}  # openrouter deliberately absent
    # Resolving groq's actual dependency chain must succeed even though
    # its fallback (openrouter) was never registered as a dependency.
    assert resolve_dependencies("groq", dependency_map) == ["groq"]


# ---------------------------------------------------------------------------
# Capability vocabulary reconciliation
# ---------------------------------------------------------------------------

def test_reconciled_capabilities_are_registerable(registries):
    capabilities, _providers, _resources, _tools = registries
    for cap_id in ("summarization", "classification", "embedding"):
        capabilities.register(Capability(capability_id=cap_id, name=cap_id.title()))
    assert {c.capability_id for c in capabilities.list_all()} == {
        "summarization",
        "classification",
        "embedding",
    }


def test_rejected_capabilities_still_rejected(registries):
    from core.registry.capability_registry import UnknownCapabilityError

    capabilities, _providers, _resources, _tools = registries
    # fast_general and frontier_escalation were deliberately NOT added to
    # the canonical vocabulary (ADR-042) -- confirm they still raise.
    with pytest.raises(UnknownCapabilityError):
        capabilities.register(Capability(capability_id="fast_general", name="Fast General"))
    with pytest.raises(UnknownCapabilityError):
        capabilities.register(Capability(capability_id="frontier_escalation", name="Frontier Escalation"))


def test_known_capabilities_is_union_of_a_and_reconciled_b_values():
    original_a_values = {
        "reasoning", "coding", "web_search", "vision", "tool_use",
        "mcp", "browser", "terminal", "memory", "planning",
    }
    reconciled_additions = {"summarization", "classification", "embedding"}
    assert KNOWN_CAPABILITIES == original_a_values | reconciled_additions


# ---------------------------------------------------------------------------
# Compatibility with existing Resolution behavior (A-006)
# ---------------------------------------------------------------------------

def test_provider_resolver_still_works_with_extended_schema(registries):
    capabilities, providers, resources, tools = registries
    providers.register(
        Provider(
            provider_id="groq",
            name="Groq",
            capabilities=["coding"],
            status="STRUCTURAL",
            verification_status="verified",
            endpoints=["https://api.groq.com/openai/v1"],  # new field present
        )
    )
    capability_resolver = CapabilityResolver(capabilities, providers, tools)
    resource_resolver = ResourceResolver(capabilities, providers, resources, tools)
    resolver = ProviderResolver(capability_resolver, resource_resolver, providers)

    result = resolver.resolve_provider("coding")
    assert result.provider.provider_id == "groq"
    assert result.provider.endpoints == ["https://api.groq.com/openai/v1"]


def test_capability_resolver_finds_reconciled_capability_providers(registries):
    capabilities, providers, resources, tools = registries
    providers.register(Provider(provider_id="groq", name="Groq", capabilities=["summarization"]))
    capability_resolver = CapabilityResolver(capabilities, providers, tools)

    eligible = capability_resolver.eligible_providers("summarization")
    assert [p.provider_id for p in eligible] == ["groq"]
