"""Integration: full Model -> ToolIntent -> ToolExecution ->
Observation -> Follow-up Model Request cycle (B-005).

Uses MockProviderAdapter (deterministic, no network) driving two
turns: turn 1 emits a tool call, turn 2 (after the observation is fed
back) returns a final answer. Verifies the observation reaches the
model, a follow-up response is generated, and the loop completes.
"""

from __future__ import annotations

from neptune.application.gateway_service import ModelGatewayService
from neptune.application.observation_loop import run_observation_loop
from neptune.core.contracts.model_gateway import ContextMessage, ModelRequest
from neptune.core.contracts.router import RoutingCandidate
from neptune.core.contracts.tool_execution import ToolOutcome
from neptune.core.domain import Availability, Capability, CostClass
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter
from neptune.infrastructure.tools.echo_tool import EchoTool
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter


class _StubRegistry:
    """Same pattern as prior gateway/tool-execution integration tests:
    routes to the mock adapter without depending on
    config/registries/*.yaml."""

    def candidates_for(self, capabilities: list[Capability]):
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


def _build_gateway_and_executor():
    gateway = ModelGatewayService(
        registry=_StubRegistry(),
        router=CapabilityRouter(),
        adapters={"reference-mock": MockProviderAdapter()},
    )
    tool_registry = ToolRegistryAdapter([EchoTool()])
    executor = ToolExecutorService(tool_registry)
    return gateway, executor


def test_two_turn_cycle_completes_after_observation() -> None:
    """turn 1: model emits a tool call. turn 2 (after the observation
    is appended): model returns a final answer. Loop must complete
    with exactly 2 turns executed."""
    gateway, executor = _build_gateway_and_executor()

    request = ModelRequest(
        task_id="loop-task-1",
        session_id="loop-session-1",
        turn_id="loop-turn-1",
        capabilities=[Capability.TOOL_USE],
        context=[ContextMessage(role="user", content="please echo hello")],
        tools=[EchoTool().definition()],
    )

    result = run_observation_loop(gateway, executor, request, max_turns=5)

    assert result.completed is True
    assert result.stop_reason == "final_answer"
    assert result.turns_executed == 2
    assert result.final_result is not None
    assert result.final_result.tool_intents == []


def test_observation_reaches_the_model() -> None:
    """The final answer must reference the observation content --
    proof the observation was actually fed back into the follow-up
    request, not just discarded."""
    gateway, executor = _build_gateway_and_executor()
    request = ModelRequest(
        task_id="loop-task-2",
        session_id="loop-session-2",
        turn_id="loop-turn-2",
        capabilities=[Capability.TOOL_USE],
        context=[ContextMessage(role="user", content="please echo hello")],
        tools=[EchoTool().definition()],
    )

    result = run_observation_loop(gateway, executor, request, max_turns=5)

    assert "based on observation" in result.final_result.output_text
    assert '"echo": "hello"' in result.final_result.output_text


def test_tool_execution_recorded_in_loop_result() -> None:
    gateway, executor = _build_gateway_and_executor()
    request = ModelRequest(
        task_id="loop-task-3",
        session_id="loop-session-3",
        turn_id="loop-turn-3",
        capabilities=[Capability.TOOL_USE],
        context=[ContextMessage(role="user", content="please echo hello")],
        tools=[EchoTool().definition()],
    )

    result = run_observation_loop(gateway, executor, request, max_turns=5)

    assert len(result.tool_results) == 1
    assert result.tool_results[0].outcome == ToolOutcome.SUCCESS
    assert result.tool_results[0].tool_name == "echo"
    assert result.tool_results[0].task_id == "loop-task-3"
    assert result.tool_results[0].session_id == "loop-session-3"


def test_transcript_contains_observation_message() -> None:
    gateway, executor = _build_gateway_and_executor()
    request = ModelRequest(
        task_id="loop-task-4",
        session_id="loop-session-4",
        turn_id="loop-turn-4",
        capabilities=[Capability.TOOL_USE],
        context=[ContextMessage(role="user", content="please echo hello")],
        tools=[EchoTool().definition()],
    )

    result = run_observation_loop(gateway, executor, request, max_turns=5)

    tool_messages = [m for m in result.transcript if m.role == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == 'Tool echo returned:\n{"echo": "hello"}'


def test_no_tool_intents_completes_in_one_turn() -> None:
    """A request without tools should complete after a single call --
    the loop must not force a tool round trip that never happens."""
    gateway, executor = _build_gateway_and_executor()
    request = ModelRequest(
        task_id="loop-task-5",
        session_id="loop-session-5",
        turn_id="loop-turn-5",
        capabilities=[Capability.FAST_GENERAL],
        context=[ContextMessage(role="user", content="just say hi")],
    )

    result = run_observation_loop(gateway, executor, request, max_turns=5)

    assert result.completed is True
    assert result.turns_executed == 1
    assert result.tool_results == []
