"""Observation Feedback Loop (B-005).

Converts ToolResult into model-visible observations and drives the

    Model -> ToolIntent -> ToolExecution -> Observation -> Follow-up Model Request

cycle to completion, entirely through existing core abstractions
(ModelGateway, ToolExecutor). No provider-specific logic anywhere in
this module -- see ADR-037 for the observation message format and its
rationale.
"""

from __future__ import annotations

import json
import uuid

from pydantic import BaseModel, Field

from neptune.core.contracts.model_gateway import (
    ContextMessage,
    ModelGateway,
    ModelGatewayError,
    ModelRequest,
    ModelResult,
)
from neptune.core.contracts.tool_execution import ToolCall, ToolExecutor, ToolOutcome, ToolResult

OBSERVATION_ROLE = "tool"
DEFAULT_MAX_TURNS = 5


class ObservationMessageBuilder:
    """Deterministic ToolResult -> ContextMessage formatting.

    See ADR-037 for the exact format and its rationale. Formatting is
    a pure function of the ToolResult's fields (sorted-key JSON for
    dict payloads), so the same ToolResult always produces the same
    observation text regardless of dict insertion order or call
    history.
    """

    def build(self, tool_result: ToolResult) -> ContextMessage:
        return ContextMessage(
            role=OBSERVATION_ROLE,
            name=tool_result.tool_name,
            content=self._format(tool_result),
        )

    def _format(self, tool_result: ToolResult) -> str:
        if tool_result.outcome == ToolOutcome.SUCCESS:
            return self._format_success(tool_result)
        return self._format_failure(tool_result)

    def _format_success(self, tool_result: ToolResult) -> str:
        if tool_result.output is None:
            # Malformed: SUCCESS outcome with no output payload. A
            # correctly-behaving ToolExecutor (B-004) never produces
            # this, but the builder must handle it defensively rather
            # than raising, since ToolResult can in principle arrive
            # from anywhere.
            return (
                f"Tool {tool_result.tool_name} reported success but "
                "returned no output (malformed tool result)."
            )
        payload = json.dumps(tool_result.output, sort_keys=True)
        return f"Tool {tool_result.tool_name} returned:\n{payload}"

    def _format_failure(self, tool_result: ToolResult) -> str:
        reason = tool_result.error_message or "no error message provided"
        return f"Tool {tool_result.tool_name} failed ({tool_result.outcome.value}): {reason}"


class LoopResult(BaseModel):
    """Outcome of a full observation-feedback cycle."""

    completed: bool
    turns_executed: int
    stop_reason: str
    final_result: ModelResult | None = None
    transcript: list[ContextMessage] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)


class ObservationProcessor:
    """Executes a ModelResult's ToolIntents via a ToolExecutor and
    turns the results into observation ContextMessages ready to
    append to a follow-up ModelRequest."""

    def __init__(
        self,
        executor: ToolExecutor,
        message_builder: ObservationMessageBuilder | None = None,
    ) -> None:
        self._executor = executor
        self._message_builder = message_builder or ObservationMessageBuilder()

    def process(
        self,
        model_result: ModelResult,
        task_id: str,
        session_id: str,
        turn_id: str,
    ) -> tuple[list[ToolResult], list[ContextMessage]]:
        """Execute every tool_intent in model_result and return the
        (ToolResult, observation ContextMessage) pairs, aligned by
        index."""
        tool_results: list[ToolResult] = []
        observations: list[ContextMessage] = []
        for intent in model_result.tool_intents:
            call = ToolCall(
                call_id=intent.call_id,
                tool_name=intent.tool_name,
                arguments=intent.arguments,
                task_id=task_id,
                session_id=session_id,
                turn_id=turn_id,
            )
            result = self._executor.execute(call)
            tool_results.append(result)
            observations.append(self._message_builder.build(result))
        return tool_results, observations

    def build_follow_up_request(
        self, previous_request: ModelRequest, observations: list[ContextMessage]
    ) -> ModelRequest:
        """Determine the next model request: same task/session/turn
        and capability/budget/tool envelope as the previous request,
        with observation messages appended to context. A fresh
        correlation_id is assigned since this is a new inference
        call."""
        return previous_request.model_copy(
            update={
                "context": [*previous_request.context, *observations],
                "correlation_id": str(uuid.uuid4()),
            }
        )


def run_observation_loop(
    gateway: ModelGateway,
    executor: ToolExecutor,
    request: ModelRequest,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> LoopResult:
    """Drive Model -> ToolIntent -> ToolExecution -> Observation ->
    Follow-up Model Request until the model stops requesting tools, an
    unrecoverable Gateway error occurs, or max_turns is reached.

    No provider-specific logic: this function only ever calls
    gateway.infer() and executor.execute() -- both Protocol-typed core
    boundaries. It does not know or care which provider or which
    tools are behind them.
    """
    processor = ObservationProcessor(executor)
    current_request = request
    all_tool_results: list[ToolResult] = []
    transcript: list[ContextMessage] = list(request.context)

    for turn in range(1, max_turns + 1):
        try:
            result = gateway.infer(current_request)
        except ModelGatewayError as exc:
            return LoopResult(
                completed=False,
                turns_executed=turn - 1,
                stop_reason=f"gateway_error: {exc.error.error_type.value}: {exc.error.message}",
                final_result=None,
                transcript=transcript,
                tool_results=all_tool_results,
            )

        if not result.tool_intents:
            return LoopResult(
                completed=True,
                turns_executed=turn,
                stop_reason="final_answer",
                final_result=result,
                transcript=transcript,
                tool_results=all_tool_results,
            )

        tool_results, observations = processor.process(
            result,
            task_id=current_request.task_id,
            session_id=current_request.session_id,
            turn_id=current_request.turn_id,
        )
        all_tool_results.extend(tool_results)
        transcript.extend(observations)
        current_request = processor.build_follow_up_request(current_request, observations)

    return LoopResult(
        completed=False,
        turns_executed=max_turns,
        stop_reason="max_turns_exceeded",
        final_result=None,
        transcript=transcript,
        tool_results=all_tool_results,
    )
