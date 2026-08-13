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
    if tools were offered, emits one canned ToolIntent so the full
    ModelResult.tool_intents path is exercised too."""

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
        tool_intents: list[ToolIntent] = []
        if request.tools:
            tool_intents.append(
                ToolIntent(
                    call_id="mock-call-1",
                    tool_name=request.tools[0].name,
                    arguments={},
                )
            )
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResult(
            output_text=f"[mock:{request.model_id}] echo: {last_user}",
            tool_intents=tool_intents,
            usage=ModelUsage(
                input_tokens=sum(len(m.content.split()) for m in request.messages),
                output_tokens=len(last_user.split()),
                total_tokens=None,
                cost_estimate_usd=0.0,
            ),
            latency_ms=latency_ms,
            finish_reason="stop",
        )
