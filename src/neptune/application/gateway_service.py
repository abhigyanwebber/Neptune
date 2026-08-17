"""Model Gateway implementation.

Wires Router + registry-derived candidates + a provider_id -> adapter
map into something conforming to core.contracts.model_gateway.
ModelGateway. This module is the one place allowed to translate
between the agent-facing (ModelRequest/ModelResult) and adapter-facing
(ProviderRequest/ProviderResult) shapes -- neither core module knows
about the other.
"""

from __future__ import annotations

import time

from neptune.core.contracts.model_gateway import (
    ModelError,
    ModelGatewayError,
    ModelRequest,
    ModelResult,
    SelectedModelMetadata,
)
from neptune.core.contracts.provider_adapter import (
    ProviderAdapter,
    ProviderInvocationError,
    ProviderRequest,
)
from neptune.core.contracts.router import NoViableCandidateError, Router
from neptune.core.domain import ErrorType
from neptune.infrastructure.models.registry import ModelRegistry


class ModelGatewayService:
    """Reference ModelGateway implementation."""

    def __init__(
        self,
        registry: ModelRegistry,
        router: Router,
        adapters: dict[str, ProviderAdapter],
    ) -> None:
        self._registry = registry
        self._router = router
        self._adapters = adapters

    def infer(self, request: ModelRequest) -> ModelResult:
        candidates = self._registry.candidates_for(request.capabilities)

        try:
            decision = self._router.select(
                correlation_id=request.correlation_id,
                requirements=request.capabilities,
                candidates=candidates,
                budget=request.budget,
                routing_constraints=request.routing_constraints,
            )
        except NoViableCandidateError as exc:
            raise ModelGatewayError(
                ModelError(
                    correlation_id=request.correlation_id,
                    error_type=ErrorType.INVALID_REQUEST,
                    message=str(exc),
                    retriable=False,
                )
            ) from exc

        chain = [decision.selected, *decision.fallback_chain]
        last_error: ProviderInvocationError | None = None

        for candidate in chain:
            adapter = self._adapters.get(candidate.provider_id)
            if adapter is None:
                continue
            try:
                return self._invoke_adapter(request, candidate.model_id, adapter)
            except ProviderInvocationError as exc:
                last_error = exc
                if not exc.retriable:
                    break
                continue

        raise ModelGatewayError(
            ModelError(
                correlation_id=request.correlation_id,
                error_type=last_error.error_type if last_error else ErrorType.PROVIDER_UNAVAILABLE,
                message=last_error.message if last_error else "no adapter available for any candidate",
                retriable=False,
                provider_id=last_error.provider_id if last_error else None,
            )
        )

    def _invoke_adapter(
        self, request: ModelRequest, model_id: str, adapter: ProviderAdapter
    ) -> ModelResult:
        provider_request = ProviderRequest(
            correlation_id=request.correlation_id,
            model_id=model_id,
            messages=request.context,
            tools=request.tools,
            max_output_tokens=request.budget.max_output_tokens,
        )
        start = time.perf_counter()
        result = adapter.invoke(provider_request)
        latency_ms = result.latency_ms
        if latency_ms is None:
            latency_ms = (time.perf_counter() - start) * 1000

        return ModelResult(
            correlation_id=request.correlation_id,
            output_text=result.output_text,
            tool_intents=result.tool_intents,
            selected_model=SelectedModelMetadata(
                model_id=model_id,
                provider_id=adapter.provider_id,
                capabilities_matched=request.capabilities,
            ),
            usage=result.usage,
            latency_ms=latency_ms,
            finish_reason=result.finish_reason,
        )
