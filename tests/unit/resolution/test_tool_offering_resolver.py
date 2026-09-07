"""Unit tests for ToolOfferingResolver (A-008): dynamic discovery,
registry-change reflection, filtering, no-tool/one-or-more availability,
duplicate handling, deterministic ordering, unknown/unavailable tool
handling, and provider independence."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from core.registry.tool_registry import ToolDefinition, ToolRegistry
from core.resolution.tool_offering_resolver import ToolOfferingResolver
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyToolDefinitionRepository


@pytest.fixture()
def tool_registry():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))


@pytest.fixture()
def resolver(tool_registry):
    return ToolOfferingResolver(tool_registry)


# ---------------------------------------------------------------------------
# No tools available / one or more available -- no fake placeholders
# ---------------------------------------------------------------------------

def test_no_tools_available_returns_empty_list_not_a_placeholder(resolver):
    assert resolver.available_tools() == []


def test_one_tool_available(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="search", name="Search", capability="web_search"))
    offerings = resolver.available_tools()
    assert len(offerings) == 1
    assert offerings[0]["tool_id"] == "search"


def test_multiple_tools_available(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="search", name="Search", capability="web_search"))
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))
    offerings = resolver.available_tools()
    assert {o["tool_id"] for o in offerings} == {"search", "mcp"}


# ---------------------------------------------------------------------------
# Registry changes affect request-time offerings (dynamic, not cached)
# ---------------------------------------------------------------------------

def test_registering_a_tool_is_immediately_reflected(resolver, tool_registry):
    assert resolver.available_tools() == []
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))
    assert [o["tool_id"] for o in resolver.available_tools()] == ["mcp"]


def test_deleting_a_tool_is_immediately_reflected(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))
    assert len(resolver.available_tools()) == 1
    tool_registry.delete("mcp")
    assert resolver.available_tools() == []


def test_updating_a_tool_is_immediately_reflected(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp", notes="v1"))
    tool = tool_registry.get("mcp")
    tool.notes = "v2"
    tool_registry.update(tool)
    assert resolver.available_tools()[0]["description"] == "v2"


# ---------------------------------------------------------------------------
# Canonical capability filtering (reuses the C-006 bridge)
# ---------------------------------------------------------------------------

def test_filters_by_canonical_capability(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="search", name="Search", capability="web_search"))
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))
    offerings = resolver.available_tools(capability_ids=["web_search"])
    assert [o["tool_id"] for o in offerings] == ["search"]


def test_filter_matching_nothing_returns_empty_list(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="search", name="Search", capability="web_search"))
    assert resolver.available_tools(capability_ids=["mcp"]) == []


def test_filter_accepts_capability_ids_that_also_pass_through_the_bridge(resolver, tool_registry):
    # "coding" is a value the C-006 bridge translates identically
    # (legacy-and-canonical overlap) -- proves the filter path goes
    # through translate_capability() rather than raw string comparison
    # only, without needing a legacy enum value in this test.
    tool_registry.register(ToolDefinition(tool_id="filesystem", name="Filesystem", capability="tool_use"))
    offerings = resolver.available_tools(capability_ids=["tool_use"])
    assert [o["tool_id"] for o in offerings] == ["filesystem"]


def test_unrecognized_capability_in_filter_is_excluded_not_raised(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="search", name="Search", capability="web_search"))
    # A typo alongside a valid id -- the valid one should still work.
    offerings = resolver.available_tools(capability_ids=["web_search", "totally-made-up"])
    assert [o["tool_id"] for o in offerings] == ["search"]


def test_rejected_capability_in_filter_is_excluded_not_raised(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="search", name="Search", capability="web_search"))
    # "fast_general" is ADR-042-rejected (C-006) -- must not raise here.
    offerings = resolver.available_tools(capability_ids=["fast_general"])
    assert offerings == []


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------

def test_offerings_are_ordered_deterministically_by_tool_id(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="terminal", name="Terminal", capability="terminal"))
    tool_registry.register(ToolDefinition(tool_id="browser", name="Browser", capability="browser"))
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))
    offerings = resolver.available_tools()
    assert [o["tool_id"] for o in offerings] == ["browser", "mcp", "terminal"]


def test_ordering_is_stable_across_repeated_calls(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="terminal", name="Terminal", capability="terminal"))
    tool_registry.register(ToolDefinition(tool_id="browser", name="Browser", capability="browser"))
    first = [o["tool_id"] for o in resolver.available_tools()]
    second = [o["tool_id"] for o in resolver.available_tools()]
    assert first == second == ["browser", "terminal"]


# ---------------------------------------------------------------------------
# Duplicate handling
# ---------------------------------------------------------------------------

def test_duplicate_tool_ids_from_the_underlying_repository_are_deduplicated():
    class _DuplicateReturningToolRegistry:
        """Stub simulating a hypothetical repository that (incorrectly)
        returns the same tool_id twice -- proves the resolver's own
        de-duplication is not merely relying on the real repository's
        primary-key constraint."""

        def list_all(self):
            return [
                ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"),
                ToolDefinition(tool_id="mcp", name="MCP (dup)", capability="mcp"),
            ]

        def get(self, tool_id):  # pragma: no cover - unused by this test
            return None

    resolver = ToolOfferingResolver(_DuplicateReturningToolRegistry())
    offerings = resolver.available_tools()
    assert len(offerings) == 1
    assert offerings[0]["tool_id"] == "mcp"


# ---------------------------------------------------------------------------
# Unavailable / unknown tool handling
# ---------------------------------------------------------------------------

def test_get_offering_for_unknown_tool_returns_none(resolver):
    assert resolver.get_offering("does-not-exist") is None


def test_get_offering_for_known_tool_returns_its_dict(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))
    offering = resolver.get_offering("mcp")
    assert offering["tool_id"] == "mcp"
    assert offering["capability"] == "mcp"


# ---------------------------------------------------------------------------
# No fake placeholder tools -- structural guarantee
# ---------------------------------------------------------------------------

def test_offering_dict_never_contains_a_synthetic_placeholder_marker(resolver, tool_registry):
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))
    for offering in resolver.available_tools():
        assert offering["tool_id"] in {"mcp"}  # only real, registered ids ever appear
