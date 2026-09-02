"""Unit tests: CanonicalRegistryCandidateSource (B-008).

Covers: provider/model resolution interaction, model-id vs
registry-key correctness (the B-003 bug fix, preserved through the
canonical-registry swap), and the multi-eligible-provider fallback
behavior. Requires live Postgres with the seed data loaded (same
registry the rest of the canonical-registry test suite uses) --
skips cleanly if unreachable, matching the project's existing
Postgres-dependent test discipline.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.resource_resolver import ResourceResolver
from infrastructure.persistence.database import make_engine, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyModelRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)

from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Availability, Capability
from neptune.infrastructure.models.canonical_registry_adapter import (
    CanonicalRegistryCandidateSource,
)


def _postgres_available() -> bool:
    try:
        engine = make_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


@pytest.fixture
def canonical_source() -> CanonicalRegistryCandidateSource:
    engine = make_engine(get_database_url())
    sf = make_session_factory(engine)
    cap_reg = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    prov_reg = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    res_reg = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    tool_reg = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    model_reg = CanonicalModelRegistry(SqlAlchemyModelRepository(sf))

    cap_resolver = CapabilityResolver(cap_reg, prov_reg, tool_reg)
    res_resolver = ResourceResolver(cap_reg, prov_reg, res_reg, tool_reg)
    prov_resolver = ProviderResolver(cap_resolver, res_resolver, prov_reg)

    return CanonicalRegistryCandidateSource(prov_resolver, model_reg)


def test_resolves_groq_model_for_coding_capability(
    canonical_source: CanonicalRegistryCandidateSource,
) -> None:
    """At least one groq candidate must be present. Not asserting an
    exact count: this Postgres instance is shared with Claude A's own
    registry-recovery tests (tests/integration/registry/
    _model_recovery_script.py), which deliberately re-registers a
    second, differently-named groq model as their own fixture data
    when the full suite runs -- that is expected, intentional
    behavior on their side, not pollution this test should fail on."""
    candidates = canonical_source.candidates_for([Capability.CODING])
    groq_candidates = [c for c in candidates if c.provider_id == "groq"]
    assert len(groq_candidates) >= 1
    assert isinstance(groq_candidates[0], RoutingCandidate)


def test_model_id_is_provider_facing_name_not_registry_key(
    canonical_source: CanonicalRegistryCandidateSource,
) -> None:
    """The B-003 bug fix, preserved: model_id must be the
    provider-facing name Groq's API actually expects ("openai/gpt-oss-120b" as of this test's writing),
    never "groq-<something>" (the registry's own entry key). Sending
    the entry key instead of the provider-facing name caused a real
    404 in B-003."""
    candidates = canonical_source.candidates_for([Capability.CODING])
    groq_candidate = next(c for c in candidates if c.model_id == "openai/gpt-oss-120b")
    assert groq_candidate.provider_id == "groq"
    assert not groq_candidate.model_id.startswith("groq-")


def test_candidate_capabilities_translated_from_canonical_vocabulary(
    canonical_source: CanonicalRegistryCandidateSource,
) -> None:
    candidates = canonical_source.candidates_for([Capability.TOOL_USE])
    groq_candidate = next(c for c in candidates if c.model_id == "openai/gpt-oss-120b")
    assert Capability.TOOL_USE in groq_candidate.capabilities
    assert Capability.CODING in groq_candidate.capabilities


def test_candidate_availability_reflects_canonical_model_status(
    canonical_source: CanonicalRegistryCandidateSource,
) -> None:
    candidates = canonical_source.candidates_for([Capability.CODING])
    groq_candidate = next(c for c in candidates if c.model_id == "openai/gpt-oss-120b")
    assert groq_candidate.availability == Availability.AVAILABLE


def test_returns_candidates_from_multiple_eligible_providers_not_just_top_ranked(
    canonical_source: CanonicalRegistryCandidateSource,
) -> None:
    """ProviderResolver's top pick for 'coding' need not be Groq (it
    may rank Gemini/OpenRouter/Ollama higher by its own criteria) --
    this class must still surface Groq's models, since it is the only
    provider Neptune has a real ProviderAdapter and registered models
    for. Regression test for the bug found during B-008 development:
    an earlier version only queried the single top-ranked provider and
    silently returned zero candidates whenever that provider had no
    registered models."""
    candidates = canonical_source.candidates_for([Capability.CODING])
    provider_ids = {c.provider_id for c in candidates}
    assert "groq" in provider_ids


def test_no_capabilities_returns_empty() -> None:
    from unittest.mock import MagicMock

    source = CanonicalRegistryCandidateSource(MagicMock(), MagicMock())
    assert source.candidates_for([]) == []


def test_unresolvable_capability_returns_empty(
    canonical_source: CanonicalRegistryCandidateSource,
) -> None:
    """FAST_GENERAL has no canonical equivalent (capability_bridge.py's
    REJECTED_EXTERNAL_CAPABILITIES) -- must degrade to an empty
    candidate list, not raise, so ModelGatewayService's existing
    NoViableCandidateError path handles it the same way it already
    handles "nothing matched" for the legacy registry."""
    candidates = canonical_source.candidates_for([Capability.FAST_GENERAL])
    assert candidates == []
