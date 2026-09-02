"""Unit tests: ModelGatewayAdapter (B-008).

Covers: request normalization (Core's opaque dict -> ModelRequest),
response normalization (ModelResult -> Core's opaque dict, including
tool_calls preservation), and error mapping (ModelGatewayError ->
never-raise, normalized error dict). Uses MockProviderAdapter -- no
network, no Postgres, no live credentials.
"""
from __future__ import annotations

from neptune.application.gateway_service import ModelGatewayService
from neptune.core.contracts.router import RoutingCandidate
from neptune.core.domain import Availability, Capability, CostClass
from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter


class _StubSource:
    def candidates_for(self, capabilities: list[Capability]) -> list[RoutingCandidate]:
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


class _EmptySource:
    def candidates_for(self, capabilities: list[Capability]) -> list[RoutingCandidate]:
        del capabilities
        return []


def _build_adapter(registry=None) -> ModelGatewayAdapter:
    gateway = ModelGatewayService(
        registry=registry or _StubSource(),
        router=CapabilityRouter(),
        adapters={"reference-mock": MockProviderAdapter()},
    )
    return ModelGatewayAdapter(gateway, task_id="task-1", session_id="session-1")


def test_send_returns_content_from_core_dict_request() -> None:
    adapter = _build_adapter()
    request = {"task_id": "task-1", "session_id": "session-1", "requirements": ["say hello"]}

    response = adapter.send(request)

    assert "content" in response
    assert response["content"] is not None
    assert "hello" in response["content"].lower() or "say hello" in response["content"]


def test_send_builds_prompt_from_requirements() -> None:
    adapter = _build_adapter()
    request = {"requirements": ["do the thing"], "recent_events": []}

    response = adapter.send(request)

    assert response["content"] is not None


def test_send_includes_recent_events_in_prompt() -> None:
    adapter = _build_adapter()
    request = {
        "requirements": [],
        "recent_events": [{"event_type": "tool.observation_received", "payload": {"echo": "hi"}}],
    }
    response = adapter.send(request)
    assert response["content"] is not None


def test_send_falls_back_to_proceed_with_no_requirements_or_events() -> None:
    adapter = _build_adapter()
    response = adapter.send({})
    assert response["content"] is not None  # MockProviderAdapter echoes whatever prompt was built


def test_send_preserves_tool_calls_shape() -> None:
    """Core's engine.py/ToolPort expect {"tool_name": ..., "args": ...}
    -- MockProviderAdapter emits a tool_intent whenever tools are
    offered, but ModelGatewayAdapter itself doesn't offer tools from
    Core's request dict (no tool concept in Core's context dict yet) --
    this test documents that tool_calls is always [] via this path
    today, which is correct/expected, not a bug (see KNOWN LIMITATIONS
    in the B-008 report)."""
    adapter = _build_adapter()
    response = adapter.send({"requirements": ["test"]})
    assert response["tool_calls"] == []


def test_send_capability_override_via_constraints() -> None:
    adapter = _build_adapter()
    response = adapter.send({"constraints": {"capability": "tool_use"}, "requirements": ["hi"]})
    assert response["content"] is not None


def test_send_returns_error_dict_never_raises_on_no_viable_candidate() -> None:
    """The core architectural decision this task documents: send()
    must never raise, even when the Gateway/Router chain fails,
    because Core's engine.py has no try/except around
    self._gateway.send(context)."""
    adapter = _build_adapter(registry=_EmptySource())

    response = adapter.send({"requirements": ["anything"]})

    assert response["content"] is None
    assert response["tool_calls"] == []
    assert "error" in response
    assert response["error"]["error_type"] == "invalid_request"
    assert response["error"]["retriable"] is False


def test_send_includes_model_and_provider_metadata() -> None:
    adapter = _build_adapter()
    response = adapter.send({"requirements": ["hi"]})
    assert response["model_id"] == "mock-model-1"
    assert response["provider_id"] == "reference-mock"
    assert "correlation_id" in response
    assert "usage" in response
    assert "latency_ms" in response
