"""Integration-level test (A-008): canonical registry -> dynamic tool
offering -> ModelGateway request, without requiring a live provider.

Uses MockProviderAdapter (the same test double every other
ModelGatewayAdapter unit test already uses) so this proves the *wiring*
(registry -> resolver -> adapter -> request), not live model behavior.
SQLite for the registry, no Docker/Postgres required -- consistent with
core.resolution's other resolver tests.
"""
from __future__ import annotations

from sqlalchemy import create_engine

from core.registry.tool_registry import ToolDefinition, ToolRegistry
from core.resolution.tool_offering_resolver import ToolOfferingResolver
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyToolDefinitionRepository
from neptune.application.gateway_service import ModelGatewayService
from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Availability, Capability, CostClass
from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter


class _StubSource:
    def candidates_for(self, capabilities):
        del capabilities
        return [
            RoutingCandidate(
                model_id="mock-model-1",
                provider_id="reference-mock",
                capabilities=[Capability.FAST_GENERAL, Capability.TOOL_USE, Capability.CODING],
                cost_class=CostClass.FREE,
                availability=Availability.AVAILABLE,
            )
        ]


def _build_tool_registry() -> ToolRegistry:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))


def _build_adapter() -> ModelGatewayAdapter:
    gateway = ModelGatewayService(
        registry=_StubSource(),
        router=CapabilityRouter(),
        adapters={"reference-mock": MockProviderAdapter()},
    )
    return ModelGatewayAdapter(gateway, task_id="task-1", session_id="session-1")


def test_registry_tool_flows_through_resolver_into_the_gateway_request():
    tool_registry = _build_tool_registry()
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))

    resolver = ToolOfferingResolver(tool_registry)
    offerings = resolver.available_tools()
    assert offerings, "sanity check: the tool we just registered must appear"

    adapter = _build_adapter()
    response = adapter.send({"requirements": ["do something"], "available_tools": offerings})

    # MockProviderAdapter emits a tool_intent whenever tools are present
    # in the request it receives -- a non-empty tool_calls here is
    # direct evidence the registry-sourced offering actually reached the
    # (mocked) provider request, not just that the resolver ran.
    assert response["tool_calls"] != []
    assert response["tool_calls"][0]["tool_name"] == "mcp"


def test_no_registered_tools_means_no_tools_offered_to_the_gateway():
    tool_registry = _build_tool_registry()  # empty
    resolver = ToolOfferingResolver(tool_registry)
    offerings = resolver.available_tools()
    assert offerings == []

    adapter = _build_adapter()
    response = adapter.send({"requirements": ["do something"], "available_tools": offerings})

    assert response["tool_calls"] == []


def test_capability_filtered_offering_reaches_the_gateway_request():
    tool_registry = _build_tool_registry()
    tool_registry.register(ToolDefinition(tool_id="search", name="Search", capability="web_search"))
    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))

    resolver = ToolOfferingResolver(tool_registry)
    offerings = resolver.available_tools(capability_ids=["mcp"])
    assert [o["tool_id"] for o in offerings] == ["mcp"]

    adapter = _build_adapter()
    response = adapter.send({"requirements": ["do something"], "available_tools": offerings})

    assert response["tool_calls"][0]["tool_name"] == "mcp"


def test_registry_change_between_requests_changes_what_the_gateway_receives():
    """Proves "request-time" discovery, not a snapshot taken once --
    two separate send() calls, separated by a registry mutation, must
    reflect the registry's state at the time of each call."""
    tool_registry = _build_tool_registry()
    resolver = ToolOfferingResolver(tool_registry)
    adapter = _build_adapter()

    first_response = adapter.send(
        {"requirements": ["step 1"], "available_tools": resolver.available_tools()}
    )
    assert first_response["tool_calls"] == []  # nothing registered yet

    tool_registry.register(ToolDefinition(tool_id="mcp", name="MCP", capability="mcp"))

    second_response = adapter.send(
        {"requirements": ["step 2"], "available_tools": resolver.available_tools()}
    )
    assert second_response["tool_calls"][0]["tool_name"] == "mcp"


def test_static_constructor_fallback_still_works_when_no_available_tools_key_present():
    """Backward compatibility (A-008 requirement: preserve B-008
    behavior) -- a caller that never supplies request["available_tools"]
    (e.g. test_full_live_agent_loop.py, unmodified by this task) must
    keep using the constructor-injected static list exactly as before."""
    gateway = ModelGatewayService(
        registry=_StubSource(),
        router=CapabilityRouter(),
        adapters={"reference-mock": MockProviderAdapter()},
    )
    from neptune.core.contracts.model_gateway import ToolDefinition as NeptuneToolDefinition

    adapter = ModelGatewayAdapter(
        gateway,
        task_id="task-1",
        session_id="session-1",
        tool_definitions=[NeptuneToolDefinition(name="echo", description="Echoes input")],
    )

    response = adapter.send({"requirements": ["do something"]})  # no "available_tools" key at all

    assert response["tool_calls"][0]["tool_name"] == "echo"
