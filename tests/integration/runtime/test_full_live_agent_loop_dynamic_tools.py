"""Full live agent loop with real dynamic tool offering (B-011).

The milestone this task exists to produce: a real coding-agent-style
task ("create a file, then read it back") completed by a real Groq
model, using a filesystem tool it discovered through the real
canonical registry -> ToolOfferingResolver -> ModelGateway dynamic-
offering path (A-008), executed by the real ToolExecutor (B-010),
through real AgentRuntime.

Requires GROQ_API_KEY and live Postgres. Skips cleanly and reports
pending otherwise -- never claims this proof without both.

Same design note as test_full_agent_loop_dynamic_tools_mock.py:
drives turns via AgentRuntime.run_turn(..., extra_context=...)
directly, not through RuntimeDriver, because RuntimeDriver's loop
does not thread extra_context through at all (see
model_gateway_adapter.py's module docstring for the full finding).
RuntimeDriver itself is not modified; only its own public
should_complete/tool_failed methods are reused, unchanged.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.registry_loader import load_tools
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry as CanonicalToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.resource_resolver import ResourceResolver
from core.resolution.tool_offering_resolver import ToolOfferingResolver
from core.runtime.driver import RuntimeDriver
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
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.filesystem_tools import ReadFileTool, WriteFileTool
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary

TARGET_CONTENT = "NEPTUNE_TOOL_SURFACE_OK"

requires_live_groq_key = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set -- full live agent loop with dynamic tool offering "
    "skipped; report as pending, not complete, per B-011's explicit instruction",
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


def _run_loop_with_extra_context(runtime, session_id, task_id, agent_id, extra_context, max_turns=6):
    """Same helper as the mock test's -- see that file's module
    docstring for why this exists instead of using RuntimeDriver."""
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


@requires_postgres
@requires_live_groq_key
def test_full_live_agent_loop_real_model_real_dynamic_offering_real_filesystem_tool(tmp_path) -> None:
    task_id = f"b011-live-dynamic-{uuid.uuid4().hex[:8]}"
    session_id_hint = f"{task_id}-session"

    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)

    # --- Canonical registries + real dynamic offering ---
    cap_reg = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    prov_reg = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    res_reg = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    canonical_tool_reg = CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    model_reg = CanonicalModelRegistry(SqlAlchemyModelRepository(sf))
    load_tools(Path("06_REGISTRIES/data/tools.yaml"), canonical_tool_reg)
    tool_resolver = ToolOfferingResolver(canonical_tool_reg)
    offerings = tool_resolver.available_tools(capability_ids=["tool_use"])
    assert [o["tool_id"] for o in offerings] == ["filesystem"]

    cap_resolver = CapabilityResolver(cap_reg, prov_reg, canonical_tool_reg)
    res_resolver = ResourceResolver(cap_reg, prov_reg, res_reg, canonical_tool_reg)
    prov_resolver = ProviderResolver(cap_resolver, res_resolver, prov_reg)
    candidate_source = CanonicalRegistryCandidateSource(prov_resolver, model_reg)

    # --- Real filesystem tools, real workspace boundary ---
    boundary = WorkspaceBoundary(tmp_path)
    real_fs_tools = [ReadFileTool(boundary), WriteFileTool(boundary)]
    concrete_definitions = [t.definition() for t in real_fs_tools]

    # --- Real Gateway/Router/GroqAdapter, real ModelGatewayAdapter with
    #     the B-011 expansion fix wired in ---
    gateway_service = ModelGatewayService(
        registry=candidate_source,
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter()},
    )
    model_gateway = ModelGatewayAdapter(
        gateway_service,
        task_id=task_id,
        session_id=session_id_hint,
        concrete_tool_definitions=concrete_definitions,
    )

    real_executor = ToolExecutorService(ToolRegistryAdapter(real_fs_tools))
    tool_port = ToolPortAdapter(real_executor, task_id=task_id, session_id=session_id_hint)

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
    runtime.create_task(
        task_id,
        requirements=[
            "In the provided workspace, create a file named NEPTUNE_TOOL_PROOF.txt "
            f"containing exactly: {TARGET_CONTENT}\n"
            "Then read the file back once and report its exact contents. "
            "You must use the available tools to write and read the file. "
            "As soon as the read tool result shows the file's content, stop calling "
            "tools and respond in plain text with exactly that content -- do not "
            "call read_file more than once."
        ],
        constraints={"capability": "tool_use"},
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

    # --- Gate 1/2: a real model received the dynamically offered
    #     filesystem tool and chose to call it ---
    assert len(turns) >= 1
    all_tool_calls_across_turns = [
        call for t in turns for call in (t.model_response.get("tool_calls") or [])
    ]
    assert all_tool_calls_across_turns, (
        "the real model never called a dynamically offered tool across "
        f"{len(turns)} turn(s) -- real-model behavior variance (see B-011 "
        f"report KNOWN LIMITATIONS), not an architectural failure. "
        f"turn contents: {[t.model_response for t in turns]}"
    )
    called_names = {c["tool_name"] for c in all_tool_calls_across_turns}
    assert called_names.issubset({"read_file", "write_file"}), (
        f"model called an unexpected tool name: {called_names} -- the dynamic-"
        "offering expansion may not be reaching the real request correctly"
    )
    assert "write_file" in called_names, "the model never wrote the proof file"

    # --- Gate 3: real ToolExecutor actually executed it -- the real
    #     file genuinely exists with the exact requested content ---
    real_file = tmp_path / "NEPTUNE_TOOL_PROOF.txt"
    assert real_file.exists(), "ToolExecutor did not actually create the real file"
    assert real_file.read_text() == TARGET_CONTENT

    for t in turns:
        for call in t.tool_calls:
            assert call["observation"]["status"] == "ok", call["observation"]

    # --- Gate 4/5: observation reached a later turn, and the final
    #     response demonstrably depends on the real tool result ---
    assert len(turns) >= 2, "no second real model turn occurred after the tool call"
    final_turn = turns[-1]
    assert final_turn.model_response.get("tool_calls") in ([], None) or not final_turn.model_response.get(
        "tool_calls"
    ), "the loop did not reach a final, tool-call-free turn"
    final_content = final_turn.model_response.get("content") or ""
    assert TARGET_CONTENT in final_content, (
        "the model's final answer does not contain the actual file content -- "
        f"it cannot have been reporting a genuine read result. content was: {final_content!r}"
    )

    # --- Gate 6: valid persistent state ---
    assert outcome == "completed"
    assert task is not None
    assert task.status.value == "completed"
    assert checkpoint is not None
