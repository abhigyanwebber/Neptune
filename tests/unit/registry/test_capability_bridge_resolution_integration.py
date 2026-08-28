"""C-006 integration-level test: external capability -> translation
bridge -> canonical capability -> CapabilityResolver, without requiring
a live provider call. Uses SQLite (no Docker needed) since this proves
composition/wiring correctness, not durability -- durability of the
underlying registries is already covered by A-004/A-006's own recovery
tests, which this task does not re-prove."""
import pytest
from sqlalchemy import create_engine

from core.registry.capability_bridge import (
    RejectedExternalCapabilityError,
    UnknownExternalCapabilityError,
    translate_capabilities,
    translate_capability,
)
from core.registry.capability_registry import CapabilityRegistry
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
def capability_resolver():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    capabilities = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    providers = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    tools = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))

    # A provider registered using canonical ids, exactly as C-004's real
    # seed data does -- proving the bridge's output is directly usable
    # by the existing registry/resolution machinery with zero adaptation.
    providers.register(Provider(provider_id="groq", name="Groq", capabilities=["coding", "reasoning"]))

    return CapabilityResolver(capabilities, providers, tools)


def test_external_capability_translates_and_resolves_to_the_right_provider(capability_resolver):
    # "coding" arrives as an external (legacy/B-side) capability name --
    # the caller doesn't know or care that it happens to be spelled the
    # same as the canonical id; it goes through the bridge regardless.
    canonical_id = translate_capability("coding")

    eligible = capability_resolver.eligible_providers(canonical_id)
    assert [p.provider_id for p in eligible] == ["groq"]


def test_external_capability_list_translates_and_resolves(capability_resolver):
    canonical_ids = translate_capabilities(["coding", "reasoning"])

    for canonical_id in canonical_ids:
        eligible = capability_resolver.eligible_providers(canonical_id)
        assert [p.provider_id for p in eligible] == ["groq"]


def test_rejected_external_capability_never_reaches_the_resolver(capability_resolver):
    # ADR-042's rejection must be enforced BEFORE anything touches the
    # registry/resolver -- the resolver should never even be asked about
    # "fast_general".
    with pytest.raises(RejectedExternalCapabilityError):
        translate_capability("fast_general")


def test_unknown_external_capability_never_reaches_the_resolver(capability_resolver):
    with pytest.raises(UnknownExternalCapabilityError):
        translate_capability("not-a-real-capability")


def test_canonical_only_capability_still_resolves_normally(capability_resolver):
    # web_search has no legacy/B-side representation -- confirms the
    # bridge's passthrough doesn't break resolution for canonical-native
    # capabilities that never went through translation logic historically.
    canonical_id = translate_capability("web_search")
    assert canonical_id == "web_search"
    # No provider declares web_search in this fixture -- confirms a
    # graceful, empty (not erroring) resolution result.
    assert capability_resolver.eligible_providers(canonical_id) == []
