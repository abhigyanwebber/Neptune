"""Live gated test (B-008 required deliverable): a real Neptune request
reaches a real Groq model through the FULL real chain, including real
AgentRuntime -- not bypassing it the way B-003's smoke test did.

    real Task -> AgentRuntime.run_turn() -> ModelGatewayPort.send()
    -> ModelGatewayAdapter -> ModelGatewayService -> CapabilityRouter
    -> canonical registry resolution (CanonicalRegistryCandidateSource)
    -> GroqAdapter -> REAL Groq API -> normalized response
    -> Turn.model_response (persisted)

Requires GROQ_API_KEY. Skips cleanly otherwise -- this is the one test
in this file that needs live credentials, per the same discipline
established in B-003 (tests/test_groq_live_e2e.py).
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.resource_resolver import ResourceResolver
from core.runtime.driver import DriverConfig, RuntimeDriver
from core.runtime.engine import AgentRuntime
from infrastructure.persistence.database import create_all_tables, make_engine, make_session_factory
from infrastructure.persistence.repositories import (
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

from neptune.application.gateway_service import ModelGatewayService
from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
from neptune.infrastructure.models.canonical_registry_adapter import (
    CanonicalRegistryCandidateSource,
)
from neptune.infrastructure.providers.groq_adapter import GroqAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter
from neptune.infrastructure.tools.echo_tool import EchoTool
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter

requires_live_groq_key = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set -- live gateway test skipped (see file docstring)",
)


def _postgres_available() -> bool:
    try:
        engine = make_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


@requires_postgres
@requires_live_groq_key
def test_first_real_agent_turn_reaches_real_groq_through_agent_runtime() -> None:
    """The B-008 milestone: a real Neptune request passes through
    AgentRuntime -> ModelGatewayPort -> canonical resolution ->
    GroqAdapter -> the REAL Groq API -> a normalized response, with the
    result actually coming from the live model (not faked)."""
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

    task_id = f"b008-live-agent-turn-{uuid.uuid4().hex[:8]}"
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

    result = driver.execute_task(
        task_id,
        requirements=["Respond with exactly: NEPTUNE_GATEWAY_OK"],
        constraints={"capability": "coding"},
    )

    assert len(result.turns_run) == 1
    turn = result.turns_run[0]
    assert turn.model_response is not None
    assert "error" not in turn.model_response, turn.model_response.get("error")
    assert turn.model_response["content"] is not None
    # The real model's exact wording can vary slightly (extra
    # punctuation, a leading/trailing word) -- what B-008 actually
    # requires is that the response demonstrably came from the real
    # model, not that it matched byte-for-byte.
    assert "NEPTUNE_GATEWAY_OK" in turn.model_response["content"]
    assert turn.model_response["provider_id"] == "groq"
    assert turn.model_response["model_id"] == "openai/gpt-oss-120b"
