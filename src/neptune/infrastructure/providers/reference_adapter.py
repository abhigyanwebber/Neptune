"""Reference/mock provider adapter.

Deterministic, in-memory, no network calls. This is what the director
authorized for proving the Gateway/Router/Adapter boundary in this
task: "A mock/reference provider can receive a normalized request and
return a normalized response." It conforms to the ProviderAdapter
Protocol structurally -- there is nothing Groq/LiteLLM-specific here.
"""

from __future__ import annotations

import time

from neptune.core.contracts.model_gateway import ToolIntent, ModelUsage
from neptune.core.contracts.provider_adapter import (
    ProviderHealth,
    ProviderRequest,
    ProviderResult,
)
from neptune.core.domain import Capability, CostClass, HealthStatus


class MockProviderAdapter:
    """A deterministic stand-in provider. Echoes the last message and,
    if tools were offered and no observation is present yet in the
    conversation, emits one canned ToolIntent so the full
    ModelResult.tool_intents path is exercised too.

    Two-turn behavior (added for B-005's observation-loop tests): if a
    "tool" role message is already present in request.messages (i.e.
    an observation was fed back), this adapter treats the tool call as
    resolved and returns a final answer referencing that observation
    instead of emitting another tool_intent. This lets tests exercise
    a full Model -> ToolIntent -> Observation -> Follow-up Response
    cycle without a live provider.
    """

    provider_id = "reference-mock"

    def __init__(self, declared_capabilities: list[Capability] | None = None) -> None:
        self._capabilities = declared_capabilities or [
            Capability.FAST_GENERAL,
            Capability.TOOL_USE,
        ]

    def capabilities(self) -> list[Capability]:
        return list(self._capabilities)

    def cost_class(self) -> CostClass:
        return CostClass.FREE

    def health(self) -> ProviderHealth:
        return ProviderHealth(status=HealthStatus.HEALTHY, detail="in-memory reference adapter")

    def invoke(self, request: ProviderRequest) -> ProviderResult:
        start = time.perf_counter()
        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        observation = next(
            (m.content for m in reversed(request.messages) if m.role == "tool"),
            None,
        )

        tool_intents: list[ToolIntent] = []
        if request.tools and observation is None:
            tool_intents.append(
                ToolIntent(
                    call_id="mock-call-1",
                    tool_name=request.tools[0].name,
                    # Realistic canned arguments rather than {} -- a
                    # real model supplies arguments matching the
                    # tool's declared schema. Hardcoded to "hello"
                    # since this mock has no real reasoning; it's
                    # deterministic on purpose (B-005 tests depend on
                    # this exact value).
                    arguments={"text": "hello"},
                )
            )

        if observation is not None:
            output_text = f"[mock:{request.model_id}] final answer based on observation: {observation}"
            finish_reason = "stop"
        elif tool_intents:
            output_text = None
            finish_reason = "tool_calls"
        else:
            output_text = f"[mock:{request.model_id}] echo: {last_user}"
            finish_reason = "stop"

        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResult(
            output_text=output_text,
            tool_intents=tool_intents,
            usage=ModelUsage(
                input_tokens=sum(len(m.content.split()) for m in request.messages),
                output_tokens=len((output_text or "").split()),
                total_tokens=None,
                cost_estimate_usd=0.0,
            ),
            latency_ms=latency_ms,
            finish_reason=finish_reason,
        )
