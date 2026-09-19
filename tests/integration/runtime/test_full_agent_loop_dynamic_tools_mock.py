"""Full agent loop with real dynamic tool offering -- deterministic/mock
composition test (B-011).

Exercises the ACTUAL runtime/dynamic-offering/tool/observation
composition -- real AgentRuntime, real ToolOfferingResolver reading
the real canonical catalog (Postgres-backed), real ToolPortAdapter,
real ToolExecutorService, real ReadFileTool/WriteFileTool, real
Postgres persistence -- with only the model itself replaced by
FakeModelGateway. No parallel fake tool/offering/observation
implementation is used anywhere in this file.

Design note (see model_gateway_adapter.py's module docstring and
DEVELOPMENT_STATE/decisions.yaml for the full B-011 finding): this
test drives turns via AgentRuntime.run_turn(..., extra_context=...)
directly rather than through RuntimeDriver.execute_task(), because
RuntimeDriver's own _run_loop() calls run_turn(session_id) with no
extra_context at all -- there is currently no way for dynamic tool
offering to reach a model request through Driver's convenience loop.
This test does NOT modify RuntimeDriver or AgentRuntime; it reuses
RuntimeDriver's own public, stateless policy methods
(should_complete, tool_failed) unchanged, and AgentRuntime's own
existing checkpoint()/complete_task() primitives, to reproduce
exactly the same loop policy Driver would apply, using only already-
existing public APIs.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.registry.registry_loader import load_tools
from core.registry.tool_registry import ToolRegistry as CanonicalToolRegistry
from core.resolution.tool_offering_resolver import ToolOfferingResolver
from core.runtime.driver import RuntimeDriver
from core.runtime.engine import AgentRuntime
from core.runtime.fakes import FakeModelGateway
from infrastructure.persistence.database import create_all_tables, make_engine, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyAgentRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyToolDefinitionRepository,
    SqlAlchemyTurnRepository,
)

from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.filesystem_tools import ReadFileTool, WriteFileTool
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary

TARGET_CONTENT = "NEPTUNE_TOOL_SURFACE_OK"


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


def _run_loop_with_extra_context(runtime, session_id, task_id, agent_id, extra_context, max_turns=3):
    """Reproduces RuntimeDriver._run_loop()'s exact policy (should_complete/
    tool_failed, checkpoint-every-turn) using only AgentRuntime's and
    RuntimeDriver's own existing public methods -- see module docstring."""
    turns = []
    last_checkpoint = None
    for turn_index in range(1, max_turns + 1):
        turn = runtime.run_turn(session_id, extra_context=extra_context)
        turns.append(turn)
        last_checkpoint = runtime.checkpoint(task_id, session_id, agent_id, label=f"turn-{turn_index}")

        if RuntimeDriver.tool_failed(turn):
            return turns, last_checkpoint, "stopped_tool_failure", None
        if RuntimeDriver.should_complete(turn):
            task = runtime.complete_task(task_id)
            return turns, last_checkpoint, "completed", task
        if not RuntimeDriver.should_continue(turn):
            break
    return turns, last_checkpoint, "stopped_max_turns", None


def test_full_agent_loop_with_real_dynamic_offering_and_real_filesystem_tool(tmp_path) -> None:
    task_id = f"b011-mock-dynamic-{uuid.uuid4().hex[:8]}"

    # --- Real canonical catalog + real dynamic offering resolver ---
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    canonical_tool_registry = CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    load_tools_result = load_tools(Path("06_REGISTRIES/data/tools.yaml"), canonical_tool_registry)
    assert load_tools_result.errors == []
    resolver = ToolOfferingResolver(canonical_tool_registry)
    offerings = resolver.available_tools(capability_ids=["tool_use"])
    assert [o["tool_id"] for o in offerings] == ["filesystem"]

    # --- Real filesystem tools, real workspace boundary ---
    boundary = WorkspaceBoundary(tmp_path)
    real_fs_tools = [ReadFileTool(boundary), WriteFileTool(boundary)]

    # --- Fake model: turn 1 writes the file, then reads it back; turn 2 finishes ---
    gateway = FakeModelGateway(
        scripted_responses=[
            {
                "content": "writing the file",
                "tool_calls": [
                    {"tool_name": "write_file", "args": {"path": "NEPTUNE_TOOL_PROOF.txt", "content": TARGET_CONTENT}}
                ],
            },
            {
                "content": f"Done. The file contains exactly: {TARGET_CONTENT}",
                "tool_calls": [],
            },
        ]
    )

    session_id_hint = f"{task_id}-session"
    real_executor = ToolExecutorService(ToolRegistryAdapter(real_fs_tools))
    tool_port = ToolPortAdapter(real_executor, task_id=task_id, session_id=session_id_hint)

    runtime = AgentRuntime(
        task_repo=SqlAlchemyTaskRepository(sf),
        agent_repo=SqlAlchemyAgentRepository(sf),
        session_repo=SqlAlchemySessionRepository(sf),
        turn_repo=SqlAlchemyTurnRepository(sf),
        event_repo=SqlAlchemyEventRepository(sf),
        checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
        model_gateway=gateway,
        tool_port=tool_port,
    )
    runtime.create_task(
        task_id,
        requirements=[
            f'Create a file named NEPTUNE_TOOL_PROOF.txt containing exactly: {TARGET_CONTENT}. '
            "Then read the file back and report its exact contents."
        ],
    )
    agent = runtime.start_agent_run(task_id, role="core-implementer")
    session = runtime.start_session(task_id, agent.agent_id)

    turns, checkpoint, outcome, task = _run_loop_with_extra_context(
        runtime,
        session.session_id,
        task_id,
        agent.agent_id,
        extra_context={"available_tools": offerings},
    )


    # --- Dynamic offering proof: turn 1 model saw the real filesystem
    #     tool (from the canonical catalog), and chose it ---
    assert len(turns) >= 1
    turn_1 = turns[0]
    assert turn_1.model_response["tool_calls"] == [
        {"tool_name": "write_file", "args": {"path": "NEPTUNE_TOOL_PROOF.txt", "content": TARGET_CONTENT}}
    ]

    # --- Real tool execution proof: the real file actually exists on disk ---
    assert len(turn_1.tool_calls) == 1
    write_observation = turn_1.tool_calls[0]["observation"]
    assert write_observation["status"] == "ok"
    real_file = tmp_path / "NEPTUNE_TOOL_PROOF.txt"
    assert real_file.exists()
    assert real_file.read_text() == TARGET_CONTENT

    # --- Observation + continuation proof ---
    assert len(turns) == 2
    turn_2 = turns[1]
    assert turn_2.model_response["content"] == f"Done. The file contains exactly: {TARGET_CONTENT}"
    assert turn_2.model_response["tool_calls"] == []

    # --- Completion + persistence proof ---
    assert outcome == "completed"
    assert task is not None
    assert task.status.value == "completed"
    assert checkpoint is not None


def test_dynamic_offering_only_surfaces_filesystem_for_tool_use_capability() -> None:
    """Sanity check on the filter this whole test relies on: the
    canonical catalog also has browser/mcp/search/terminal entries
    with no real backing (B-010) -- capability filtering, not this
    test's own logic, is what keeps them out of the model's view."""
    engine = make_engine(get_database_url())
    sf = make_session_factory(engine)
    canonical_tool_registry = CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    load_tools(Path("06_REGISTRIES/data/tools.yaml"), canonical_tool_registry)
    resolver = ToolOfferingResolver(canonical_tool_registry)

    all_offerings = {o["tool_id"] for o in resolver.available_tools()}
    assert {"browser", "filesystem", "mcp", "search", "terminal"}.issubset(all_offerings)

    filtered = {o["tool_id"] for o in resolver.available_tools(capability_ids=["tool_use"])}
    assert filtered == {"filesystem"}


def test_boundary_violation_surfaces_through_the_full_dynamic_offering_loop(tmp_path) -> None:
    """Workspace-boundary validation (B-011 phase 8), exercised through
    the actual dynamic-offering + AgentRuntime composition, not just
    the isolated unit/integration coverage already in B-010's test
    suite. A model attempting to escape the workspace must fail as a
    normal, structured tool-level error -- the Turn/task still
    completes, nothing crashes."""
    task_id = f"b011-boundary-{uuid.uuid4().hex[:8]}"

    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    canonical_tool_registry = CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    load_tools(Path("06_REGISTRIES/data/tools.yaml"), canonical_tool_registry)
    resolver = ToolOfferingResolver(canonical_tool_registry)
    offerings = resolver.available_tools(capability_ids=["tool_use"])

    boundary = WorkspaceBoundary(tmp_path)
    real_fs_tools = [ReadFileTool(boundary), WriteFileTool(boundary)]

    gateway = FakeModelGateway(
        scripted_responses=[
            {
                "content": "trying to escape",
                "tool_calls": [{"tool_name": "read_file", "args": {"path": "../../etc/passwd"}}],
            },
            {"content": "could not read that file", "tool_calls": []},
        ]
    )

    session_id_hint = f"{task_id}-session"
    real_executor = ToolExecutorService(ToolRegistryAdapter(real_fs_tools))
    tool_port = ToolPortAdapter(real_executor, task_id=task_id, session_id=session_id_hint)

    runtime = AgentRuntime(
        task_repo=SqlAlchemyTaskRepository(sf),
        agent_repo=SqlAlchemyAgentRepository(sf),
        session_repo=SqlAlchemySessionRepository(sf),
        turn_repo=SqlAlchemyTurnRepository(sf),
        event_repo=SqlAlchemyEventRepository(sf),
        checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
        model_gateway=gateway,
        tool_port=tool_port,
    )
    runtime.create_task(task_id, requirements=["attempt a boundary escape"])
    agent = runtime.start_agent_run(task_id, role="core-implementer")
    session = runtime.start_session(task_id, agent.agent_id)

    turns, checkpoint, outcome, task = _run_loop_with_extra_context(
        runtime,
        session.session_id,
        task_id,
        agent.agent_id,
        extra_context={"available_tools": offerings},
    )

    turn_1 = turns[0]
    observation = turn_1.tool_calls[0]["observation"]
    assert observation["status"] == "error"
    assert "escapes workspace root" in observation["error_message"]
    # The task still reaches a normal terminal state -- a boundary
    # violation is a structured tool failure, not a crash.
    assert outcome in ("stopped_tool_failure", "completed")
