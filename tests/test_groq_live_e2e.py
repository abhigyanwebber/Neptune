"""Live end-to-end test: real Groq inference through the full Neptune
Gateway/Router path.

Requires GROQ_API_KEY to be set. Skipped automatically otherwise --
this is the one test in the suite that needs live credentials, per
task item 6's instruction to document any tests requiring them.

Run with:
    $env:GROQ_API_KEY = "..."
    python -m pytest tests/test_groq_live_e2e.py -v
"""

from __future__ import annotations

import os

import pytest

from neptune.application.gateway_service import ModelGatewayService
from neptune.core.contracts.model_gateway import ContextMessage, ModelRequest, ModelResult
from neptune.core.domain import Capability
from neptune.infrastructure.models.registry import ModelRegistry
from neptune.infrastructure.providers.groq_adapter import GroqAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter

requires_live_groq_key = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set -- live Groq test skipped (see file docstring)",
)


@requires_live_groq_key
def test_live_inference_round_trip(model_registry: ModelRegistry) -> None:
    """The actual B-003 stop-condition check: a Neptune request built
    from ModelRequest, routed through ModelGatewayService and
    CapabilityRouter, reaches a real Groq model and returns a
    normalized ModelResult."""
    gateway = ModelGatewayService(
        registry=model_registry,
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter()},
    )
    request = ModelRequest(
        task_id="live-e2e-task",
        session_id="live-e2e-session",
        turn_id="live-e2e-turn-1",
        capabilities=[Capability.FAST_GENERAL],
        context=[ContextMessage(role="user", content="Reply with exactly one word: hello")],
        # openai/gpt-oss-120b (swapped in during B-008 after Groq
        # retired llama-3.3-70b-versatile) is a reasoning model and
        # spends some of max_output_tokens on internal reasoning
        # before visible output -- 20 was tuned for the old model and
        # produced finish_reason="length" with empty output_text on
        # this one. 200 gives enough headroom for both.
        budget={"max_output_tokens": 200},
    )

    result = gateway.infer(request)

    assert isinstance(result, ModelResult)
    assert result.correlation_id == request.correlation_id
    assert result.selected_model.provider_id == "groq"
    assert result.output_text  # a real model produced real text
    assert result.usage is not None
    assert result.usage.total_tokens is not None and result.usage.total_tokens > 0
    assert result.latency_ms is not None and result.latency_ms > 0


@requires_live_groq_key
def test_live_health_check_reports_healthy() -> None:
    adapter = GroqAdapter()
    health = adapter.health()
    assert health.status.value == "healthy"


@requires_live_groq_key
def test_live_model_listing_returns_data() -> None:
    """Task item 4: populate provider metadata from the live
    provider. This confirms the capability-discovery path works
    end-to-end; registry files themselves are updated by a human
    reviewing scripts/probe_groq_models.py output, not automatically
    overwritten by a test."""
    adapter = GroqAdapter()
    models = adapter.list_live_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert all("id" in m for m in models)
