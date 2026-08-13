"""Groq provider adapter (scaffold).

Verified as the practical first candidate for the single-provider
vertical slice (ADR-033): free tier with no card required, OpenAI-
compatible surface (fits behind LiteLLM per ADR-032), tool calling
supported on llama-3.3-70b-versatile / gpt-oss-120b.

STATUS: scaffold only. Per director instruction this task does not
require or authorize a live provider call -- that is exercised via
MockProviderAdapter in tests instead. GROQ_API_KEY is read lazily
(only at invoke() time) so importing/constructing this class never
requires network access or a secret to be present.

Groq is not architecturally privileged: it satisfies the same
ProviderAdapter Protocol as MockProviderAdapter and is fully
replaceable (PROVIDER_CONTRACT invariant 3; ADR-001).
"""

from __future__ import annotations

import os
import time

from neptune.core.contracts.provider_adapter import (
    ProviderHealth,
    ProviderInvocationError,
    ProviderRequest,
    ProviderResult,
)
from neptune.core.domain import Capability, CostClass, ErrorType, HealthStatus


class GroqAdapter:
    """Adapter for Groq's OpenAI-compatible endpoint via LiteLLM.

    LiteLLM is imported lazily inside invoke(), not at module load, so
    that this module can be imported (and the boundary/registry tests
    can run) in environments where `litellm` isn't installed -- it is
    not a dependency of this task.
    """

    provider_id = "groq"

    _DECLARED_CAPABILITIES = [
        Capability.FAST_GENERAL,
        Capability.TOOL_USE,
        Capability.CODING,
        Capability.SUMMARIZATION,
        Capability.CLASSIFICATION,
    ]

    def capabilities(self) -> list[Capability]:
        return list(self._DECLARED_CAPABILITIES)

    def cost_class(self) -> CostClass:
        return CostClass.FREE

    def health(self) -> ProviderHealth:
        if not os.environ.get("GROQ_API_KEY"):
            return ProviderHealth(
                status=HealthStatus.UNKNOWN,
                detail="GROQ_API_KEY not set; health cannot be checked without a call",
            )
        return ProviderHealth(status=HealthStatus.UNKNOWN, detail="not probed (scaffold)")

    def invoke(self, request: ProviderRequest) -> ProviderResult:
        try:
            import litellm
        except ImportError as exc:
            raise ProviderInvocationError(
                error_type=ErrorType.PROVIDER_UNAVAILABLE,
                message="litellm is not installed; GroqAdapter is a scaffold "
                "pending the authorized live-provider vertical slice",
                retriable=False,
                provider_id=self.provider_id,
            ) from exc

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ProviderInvocationError(
                error_type=ErrorType.AUTHENTICATION,
                message="GROQ_API_KEY not set",
                retriable=False,
                provider_id=self.provider_id,
            )

        start = time.perf_counter()
        try:
            response = litellm.completion(
                model=f"groq/{request.model_id}",
                messages=[
                    {"role": m.role, "content": m.content} for m in request.messages
                ],
                max_tokens=request.max_output_tokens,
                api_key=api_key,
            )
        except Exception as exc:  # noqa: BLE001 -- normalized at the boundary
            raise ProviderInvocationError(
                error_type=ErrorType.UNKNOWN,
                message=str(exc),
                retriable=True,
                provider_id=self.provider_id,
            ) from exc
        latency_ms = (time.perf_counter() - start) * 1000

        choice = response.choices[0]
        return ProviderResult(
            output_text=choice.message.content,
            tool_intents=[],
            usage=None,
            latency_ms=latency_ms,
            finish_reason=choice.finish_reason,
        )
