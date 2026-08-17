"""Gateway boundary tests.

Proves: Neptune request -> Gateway -> Router -> Provider adapter ->
normalized response, with no provider-specific type ever crossing back
out of the Gateway (director validation items 4 and 5).
"""

from __future__ import annotations

from neptune.application.gateway_service import ModelGatewayService
from neptune.core.contracts.model_gateway import (
    ContextMessage,
    ModelRequest,
    ModelResult,
    ToolDefinition,
)
from neptune.core.contracts.provider_adapter import ProviderResult
from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Availability, Capability, CostClass
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter


class _StubRegistry:
    """A registry stand-in that returns exactly one mock candidate, so
    this test doesn't depend on config/registries/*.yaml contents."""

    def candidates_for(self, capabilities: list[Capability]) -> list[RoutingCandidate]:
        del capabilities
        return [
            RoutingCandidate(
                model_id="mock-model-1",
                provider_id="reference-mock",
                capabilities=[Capability.FAST_GENERAL, Capability.TOOL_USE],
                cost_class=CostClass.FREE,
                availability=Availability.AVAILABLE,
            )
        ]


def test_infer_round_trip_returns_normalized_result(mock_adapter: MockProviderAdapter) -> None:
    gateway = ModelGatewayService(
        registry=_StubRegistry(),
        router=CapabilityRouter(),
        adapters={"reference-mock": mock_adapter},
    )
    request = ModelRequest(
        task_id="task-1",
        session_id="session-1",
        turn_id="turn-1",
        capabilities=[Capability.FAST_GENERAL],
        context=[ContextMessage(role="user", content="hello neptune")],
    )

    result = gateway.infer(request)

    assert isinstance(result, ModelResult)
    assert result.correlation_id == request.correlation_id
    assert result.selected_model.provider_id == "reference-mock"
    assert result.selected_model.model_id == "mock-model-1"
    assert "hello neptune" in (result.output_text or "")
    assert not isinstance(result, ProviderResult)


def test_infer_with_tools_returns_tool_intent(mock_adapter: MockProviderAdapter) -> None:
    gateway = ModelGatewayService(
        registry=_StubRegistry(),
        router=CapabilityRouter(),
        adapters={"reference-mock": mock_adapter},
    )
    request = ModelRequest(
        task_id="task-1",
        session_id="session-1",
        turn_id="turn-1",
        capabilities=[Capability.TOOL_USE],
        context=[ContextMessage(role="user", content="what's the weather")],
        tools=[ToolDefinition(name="get_weather", description="Get current weather")],
    )

    result = gateway.infer(request)

    assert len(result.tool_intents) == 1
    assert result.tool_intents[0].tool_name == "get_weather"


def test_infer_falls_back_when_first_adapter_missing(mock_adapter: MockProviderAdapter) -> None:
    """RouteDecision picks a provider_id with no registered adapter;
    Gateway must not crash the caller with an unhandled KeyError --
    it should surface a normalized ModelGatewayError instead. This
    exercises the degrade-not-corrupt invariant (PROVIDER_CONTRACT #2)
    for the no-adapter-available edge case."""
    from neptune.core.contracts.model_gateway import ModelGatewayError

    gateway = ModelGatewayService(
        registry=_StubRegistry(),
        router=CapabilityRouter(),
        adapters={},  # nothing registered for "reference-mock"
    )
    request = ModelRequest(
        task_id="task-1",
        session_id="session-1",
        turn_id="turn-1",
        capabilities=[Capability.FAST_GENERAL],
    )

    try:
        gateway.infer(request)
        assert False, "expected ModelGatewayError"
    except ModelGatewayError as exc:
        assert exc.error.correlation_id == request.correlation_id
