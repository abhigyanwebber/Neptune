"""B-008 milestone script: a real Neptune request through the FULL real
chain -- AgentRuntime -> ModelGatewayPort -> canonical registry
resolution -> GroqAdapter -> the real Groq API -> a normalized
response -- superseding B-003's run_live_groq_smoke_test.py, which
bypassed AgentRuntime entirely and read the deprecated YAML registry
directly.

Usage:
    $env:GROQ_API_KEY = "..."
    $env:NEPTUNE_DATABASE_URL = "postgresql+psycopg2://neptune:neptune@localhost:5433/neptune"  # or rely on the default
    python scripts/run_live_first_agent_turn.py
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from config.settings import get_database_url  # noqa: E402
from core.registry.capability_registry import CapabilityRegistry  # noqa: E402
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry  # noqa: E402
from core.registry.provider_registry import ProviderRegistry  # noqa: E402
from core.registry.resource_registry import ResourceRegistry  # noqa: E402
from core.registry.tool_registry import ToolRegistry  # noqa: E402
from core.resolution.capability_resolver import CapabilityResolver  # noqa: E402
from core.resolution.provider_resolver import ProviderResolver  # noqa: E402
from core.resolution.resource_resolver import ResourceResolver  # noqa: E402
from core.runtime.driver import DriverConfig, RuntimeDriver  # noqa: E402
from core.runtime.engine import AgentRuntime  # noqa: E402
from infrastructure.persistence.database import (  # noqa: E402
    create_all_tables,
    make_engine,
    make_session_factory,
)
from infrastructure.persistence.repositories import (  # noqa: E402
    SqlAlchemyAgentRepository,
    SqlAlchemyCapabilityRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyModelRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyToolDefinitionRepository,
    SqlAlchemyTurnRepository,
)

from neptune.application.gateway_service import ModelGatewayService  # noqa: E402
from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter  # noqa: E402
from neptune.infrastructure.models.canonical_registry_adapter import (  # noqa: E402
    CanonicalRegistryCandidateSource,
)
from neptune.infrastructure.providers.groq_adapter import GroqAdapter  # noqa: E402
from neptune.infrastructure.routing.capability_router import CapabilityRouter  # noqa: E402
from neptune.infrastructure.tools.echo_tool import EchoTool  # noqa: E402
from neptune.infrastructure.tools.executor import ToolExecutorService  # noqa: E402
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter  # noqa: E402
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter  # noqa: E402


def main() -> int:
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)

    cap_reg = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    prov_reg = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    res_reg = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    tool_reg = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    model_reg = CanonicalModelRegistry(SqlAlchemyModelRepository(sf))
    cap_resolver = CapabilityResolver(cap_reg, prov_reg, tool_reg)
    res_resolver = ResourceResolver(cap_reg, prov_reg, res_reg, tool_reg)
    prov_resolver = ProviderResolver(cap_resolver, res_resolver, prov_reg)
    candidate_source = CanonicalRegistryCandidateSource(prov_resolver, model_reg)

    task_id = f"b008-smoke-test-task-{uuid.uuid4().hex[:8]}"
    session_id_hint = f"{task_id}-session"

    gateway_service = ModelGatewayService(
        registry=candidate_source,
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter()},
    )
    model_gateway = ModelGatewayAdapter(gateway_service, task_id=task_id, session_id=session_id_hint)

    tool_executor = ToolExecutorService(ToolRegistryAdapter([EchoTool()]))
    tool_port = ToolPortAdapter(tool_executor, task_id=task_id, session_id=session_id_hint)

    runtime = AgentRuntime(
        task_repo=SqlAlchemyTaskRepository(sf),
        agent_repo=SqlAlchemyAgentRepository(sf),
        session_repo=SqlAlchemySessionRepository(sf),
        turn_repo=SqlAlchemyTurnRepository(sf),
        event_repo=SqlAlchemyEventRepository(sf),
        checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
        model_gateway=model_gateway,
        tool_port=tool_port,
    )
    driver = RuntimeDriver(runtime, config=DriverConfig(max_turns=1))

    print(f"--> real Neptune request originating (task_id={task_id})")
    print("--> AgentRuntime/RuntimeDriver -> ModelGatewayPort -> ModelGatewayAdapter")
    print("--> canonical registry resolution -> GroqAdapter -> REAL Groq API")

    result = driver.execute_task(
        task_id,
        requirements=["Respond with exactly: NEPTUNE_GATEWAY_OK"],
        constraints={"capability": "coding"},
    )

    if not result.turns_run:
        print("XX no turns ran")
        return 1

    turn = result.turns_run[0]
    response = turn.model_response or {}
    if "error" in response:
        print(f"XX gateway error: {response['error']}")
        return 1

    print(f"<-- provider: {response.get('provider_id')} model: {response.get('model_id')}")
    print(f"<-- content: {response.get('content')!r}")
    print(f"<-- usage: {response.get('usage')}")
    print(f"<-- driver outcome: {result.outcome.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
