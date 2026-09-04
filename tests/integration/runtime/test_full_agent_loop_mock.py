"""Full agent loop -- deterministic/mock composition test (B-009).

Exercises the ACTUAL runtime/tool/observation composition -- real
AgentRuntime, real RuntimeDriver, real ToolPortAdapter, real
ToolExecutorService, real EchoTool, real Postgres persistence -- with
only the model itself replaced by FakeModelGateway (an existing,
Claude-A-authored test double built specifically for this purpose, per
its own docstring: "so Core Runtime is fully testable ... without
Claude B's real implementations"). No parallel fake tool/observation
implementation is used anywhere in this file.

Proves in one execution:
    Turn 1: AgentRuntime -> ModelGatewayPort (fake) -> tool-call decision
    Tool execution: ToolPort -> real ToolExecutor -> real EchoTool -> real ToolResult
    Observation: real ToolResult -> real observation mechanism -> model context
    Turn 2: AgentRuntime -> ModelGatewayPort (fake) -> final answer
    Completion: final answer -> successful completion -> persisted Turn/Checkpoint
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.runtime.driver import DriverConfig, RuntimeDriver
from core.runtime.engine import AgentRuntime
from core.runtime.fakes import FakeModelGateway
from infrastructure.persistence.database import create_all_tables, make_engine, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyAgentRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyTurnRepository,
)

from neptune.infrastructure.tools.echo_tool import EchoTool
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter


def _postgres_available() -> bool:
    try:
        engine = make_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


def _build_runtime(gateway: FakeModelGateway, tool_port: ToolPortAdapter) -> AgentRuntime:
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return AgentRuntime(
        task_repo=SqlAlchemyTaskRepository(sf),
        agent_repo=SqlAlchemyAgentRepository(sf),
        session_repo=SqlAlchemySessionRepository(sf),
        turn_repo=SqlAlchemyTurnRepository(sf),
        event_repo=SqlAlchemyEventRepository(sf),
        checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
        model_gateway=gateway,
        tool_port=tool_port,
    )


def test_full_agent_loop_mock_model_real_tool_execution() -> None:
    """turn 1: fake model decides to call echo. Real ToolExecutor runs
    the real EchoTool. The real observation is fed back. turn 2: fake
    model (now seeing the observation in recent_events) returns the
    final answer. All in one driver.execute_task() call, one process."""
    task_id = f"b009-mock-full-loop-{uuid.uuid4().hex[:8]}"

    gateway = FakeModelGateway(
        scripted_responses=[
            {
                "content": "calling echo",
                "tool_calls": [{"tool_name": "echo", "args": {"text": "NEPTUNE_FULL_LOOP_OK"}}],
            },
            {"content": "NEPTUNE_FULL_LOOP_DONE", "tool_calls": []},
        ]
    )
    tool_executor = ToolExecutorService(ToolRegistryAdapter([EchoTool()]))
    tool_port = ToolPortAdapter(tool_executor, task_id=task_id, session_id=f"{task_id}-session")

    runtime = _build_runtime(gateway, tool_port)
    driver = RuntimeDriver(runtime, config=DriverConfig(max_turns=2))

    result = driver.execute_task(
        task_id,
        requirements=[
            'Use the echo tool with the text "NEPTUNE_FULL_LOOP_OK". '
            "After receiving the tool result, respond with exactly: NEPTUNE_FULL_LOOP_DONE"
        ],
    )

    # --- Turn 1: model decision reached the real tool path ---
    assert len(result.turns_run) == 2
    turn_1 = result.turns_run[0]
    assert turn_1.model_response["tool_calls"] == [
        {"tool_name": "echo", "args": {"text": "NEPTUNE_FULL_LOOP_OK"}}
    ]

    # --- Tool execution: real ToolExecutor actually ran EchoTool ---
    assert len(turn_1.tool_calls) == 1
    observation = turn_1.tool_calls[0]["observation"]
    assert observation["status"] == "ok"
    assert observation["result"] == {"echo": "NEPTUNE_FULL_LOOP_OK"}

    # --- Turn 2: the model's next request carried the real observation ---
    assert len(gateway.requests_received) == 2
    turn_2_request = gateway.requests_received[1]
    recent_event_payloads = [e.get("payload") for e in turn_2_request.get("recent_events", [])]
    assert any(
        isinstance(p, dict)
        and isinstance(p.get("observation"), dict)
        and p["observation"].get("result") == {"echo": "NEPTUNE_FULL_LOOP_OK"}
        for p in recent_event_payloads
    )

    # --- Turn 2 result / completion ---
    turn_2 = result.turns_run[1]
    assert turn_2.model_response["content"] == "NEPTUNE_FULL_LOOP_DONE"
    assert turn_2.model_response["tool_calls"] == []
    assert result.outcome.value == "completed"
    assert result.task.status.value == "completed"

    # --- Persisted state / checkpoint ---
    assert result.last_checkpoint is not None
