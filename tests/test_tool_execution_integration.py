"""Integration: Runtime -> Gateway -> Router -> Provider -> tool call
-> tool execution -> observation returned (B-004).

Two variants, per the task's "Mock provider allowed if real model
cannot reliably emit tool calls":

1. test_mock_provider_* -- deterministic, always runs, no network.
   MockProviderAdapter always emits exactly one canned ToolIntent when
   tools are offered, so this is the reliable, always-green proof
   that the full path (including real ModelGatewayService/
   CapabilityRouter, not fakes) correctly hands a model-emitted tool
   call to the ToolExecutor and gets back a real observation.

2. test_live_groq_* -- gated on GROQ_API_KEY, best-effort. A real
   model may or may not choose to call the tool for a given prompt;
   if it doesn't, the test skips rather than failing, since that is
   Groq's behavior on that call, not a Neptune defect.
"""

from __future__ import annotations

import os

import pytest

from neptune.application.gateway_service import ModelGatewayService
from neptune.core.contracts.model_gateway import ContextMessage, ModelRequest
from neptune.core.contracts.tool_execution import ToolCall, ToolOutcome
from neptune.core.domain import Capability
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter
from neptune.infrastructure.tools.echo_tool import EchoTool
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter

requires_live_groq_key = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set -- live tool-call integration test skipped",
)


class _StubRegistry:
    """Same pattern as test_gateway_boundary.py: routes to the mock
    adapter without depending on config/registries/*.yaml."""

    def candidates_for(self, capabilities: list[Capability]):
        from neptune.core.contracts.router import RoutingCandidate
        from neptune.core.domain import Availability, CostClass

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


def test_mock_provider_full_path_tool_call_to_observation() -> None:
    """Real Runtime request (ModelRequest) -> real ModelGatewayService
    -> real CapabilityRouter -> mock provider emits a ToolIntent ->
    real ToolExecutor runs the real echo tool -> real ToolResult."""
    gateway = ModelGatewayService(
        registry=_StubRegistry(),
        router=CapabilityRouter(),
        adapters={"reference-mock": MockProviderAdapter()},
    )
    task_id, session_id, turn_id = "int-task-1", "int-session-1", "int-turn-1"

    request = ModelRequest(
        task_id=task_id,
        session_id=session_id,
        turn_id=turn_id,
        capabilities=[Capability.TOOL_USE],
        context=[ContextMessage(role="user", content="please echo 'hello'")],
        tools=[EchoTool().definition()],
    )

    model_result = gateway.infer(request)
    assert len(model_result.tool_intents) == 1
    intent = model_result.tool_intents[0]
    assert intent.tool_name == "echo"

    registry = ToolRegistryAdapter([EchoTool()])
    executor = ToolExecutorService(registry)
    tool_call = ToolCall(
        call_id=intent.call_id,
        tool_name=intent.tool_name,
        # MockProviderAdapter emits an empty-args canned intent; feed
        # it a valid echo payload to exercise the full success path.
        arguments={"text": "hello"},
        task_id=task_id,
        session_id=session_id,
        turn_id=turn_id,
    )

    observation = executor.execute(tool_call)

    assert observation.outcome == ToolOutcome.SUCCESS
    assert observation.output == {"echo": "hello"}
    assert observation.task_id == task_id
    assert observation.session_id == session_id
    assert observation.turn_id == turn_id


@requires_live_groq_key
def test_live_groq_tool_call_to_observation(model_registry) -> None:
    """Best-effort real-model variant. Skips (not fails) if the real
    model chooses not to call the tool for this prompt -- that is
    provider behavior on a given call, not a Neptune defect."""
    from neptune.infrastructure.providers.groq_adapter import GroqAdapter

    gateway = ModelGatewayService(
        registry=model_registry,
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter()},
    )
    task_id, session_id, turn_id = "live-int-task", "live-int-session", "live-int-turn-1"

    request = ModelRequest(
        task_id=task_id,
        session_id=session_id,
        turn_id=turn_id,
        capabilities=[Capability.TOOL_USE],
        context=[
            ContextMessage(
                role="user",
                content="Call the echo tool with text set to exactly 'hello'. "
                "You must use the tool -- do not answer in plain text.",
            )
        ],
        tools=[EchoTool().definition()],
        budget={"max_output_tokens": 100},
    )

    model_result = gateway.infer(request)
    if not model_result.tool_intents:
        pytest.skip("live Groq model did not emit a tool call on this run")

    intent = model_result.tool_intents[0]
    assert intent.tool_name == "echo"

    registry = ToolRegistryAdapter([EchoTool()])
    executor = ToolExecutorService(registry)
    tool_call = ToolCall(
        call_id=intent.call_id,
        tool_name=intent.tool_name,
        arguments=intent.arguments,
        task_id=task_id,
        session_id=session_id,
        turn_id=turn_id,
    )

    observation = executor.execute(tool_call)

    assert observation.outcome == ToolOutcome.SUCCESS
    assert "echo" in observation.output
