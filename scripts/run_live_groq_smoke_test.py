"""Runtime entrypoint stand-in for the B-003 live vertical slice.

Claude A's real Task/Session/Turn runtime (Stage 0/1) does not exist
yet in this repo -- this script is a minimal stand-in that plays the
same role: it constructs a ModelRequest exactly as a real Runtime
would, and drives it through the same Gateway/Router path a real
Runtime will use. This satisfies task item 3's requirement that "the
request must originate through Neptune contracts, not direct adapter
invocation" without duplicating or pre-empting Claude A's core work.

Usage:
    $env:GROQ_API_KEY = "..."
    python scripts/run_live_groq_smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from neptune.application.gateway_service import ModelGatewayService  # noqa: E402
from neptune.core.contracts.model_gateway import (  # noqa: E402
    ContextMessage,
    ModelGatewayError,
    ModelRequest,
)
from neptune.core.domain import Capability  # noqa: E402
from neptune.infrastructure.models.registry import ModelRegistry  # noqa: E402
from neptune.infrastructure.providers.groq_adapter import GroqAdapter  # noqa: E402
from neptune.infrastructure.routing.capability_router import CapabilityRouter  # noqa: E402

CONFIG_DIR = REPO_ROOT / "config" / "registries"


def main() -> int:
    registry = ModelRegistry.load(CONFIG_DIR)
    gateway = ModelGatewayService(
        registry=registry,
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter()},
    )

    # This is exactly what a real Runtime would build from a task/
    # session/turn -- task_id/session_id/turn_id are stand-in strings
    # here because Claude A's durable Task/Session/Turn objects don't
    # exist yet (Stage 0/1 not built). The Gateway does not care what
    # produced these identifiers; it only needs them to be strings.
    request = ModelRequest(
        task_id="smoke-test-task",
        session_id="smoke-test-session",
        turn_id="smoke-test-turn-1",
        capabilities=[Capability.FAST_GENERAL],
        context=[
            ContextMessage(
                role="user",
                content="In one short sentence, what is Neptune?",
            )
        ],
        budget={"max_output_tokens": 100},
    )

    print(f"--> Neptune request originating (correlation_id={request.correlation_id})")
    print("--> Runtime stand-in -> ModelGatewayService.infer() -> Router -> GroqAdapter")

    try:
        result = gateway.infer(request)
    except ModelGatewayError as exc:
        print(f"XX ModelGatewayError: {exc.error.error_type.value}: {exc.error.message}")
        return 1

    print(f"<-- selected model: {result.selected_model.model_id} "
          f"via provider: {result.selected_model.provider_id}")
    print(f"<-- latency: {result.latency_ms:.1f} ms")
    print(f"<-- usage: {result.usage}")
    print(f"<-- output_text: {result.output_text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
