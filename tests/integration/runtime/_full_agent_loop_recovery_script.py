"""Standalone script invoked as a SEPARATE OS process by
test_full_agent_loop_recovery.py (B-009 Phase 4).

Extends B-006's tool-execution recovery script
(_tool_execution_recovery_script.py) to the FULL loop: turn 1's tool
call and its real observation are persisted, the process exits
(simulated interruption), then a brand-new process resumes and
completes turn 2 using the persisted observation -- proving recovery
composes with the full model -> tool -> observation -> model cycle,
not just a bare tool call.

    python _full_agent_loop_recovery_script.py run_partial <task_id>
        -> one turn: fake model decides to call echo, real EchoTool
           executes, observation persisted, process exits.
    python _full_agent_loop_recovery_script.py resume_and_finish <task_id>
        -> brand-new process, fresh FakeModelGateway scripted to
           return the final answer, fresh ToolExecutor (unused this
           turn), resumes and completes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from config.settings import get_database_url  # noqa: E402
from core.runtime.driver import DriverConfig, RuntimeDriver  # noqa: E402
from core.runtime.engine import AgentRuntime  # noqa: E402
from core.runtime.fakes import FakeModelGateway  # noqa: E402
from infrastructure.persistence.database import (  # noqa: E402
    create_all_tables,
    make_engine,
    make_session_factory,
)
from infrastructure.persistence.repositories import (  # noqa: E402
    SqlAlchemyAgentRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyTurnRepository,
)

from neptune.infrastructure.tools.echo_tool import EchoTool  # noqa: E402
from neptune.infrastructure.tools.executor import ToolExecutorService  # noqa: E402
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter  # noqa: E402
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter  # noqa: E402


def _build_runtime(gateway, tool_port) -> AgentRuntime:
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


def do_run_partial(task_id: str) -> None:
    gateway = FakeModelGateway(
        default_response_fn=lambda req: {
            "content": "calling echo",
            "tool_calls": [{"tool_name": "echo", "args": {"text": "NEPTUNE_FULL_LOOP_OK"}}],
        }
    )
    session_id_hint = f"{task_id}-session"
    executor = ToolExecutorService(ToolRegistryAdapter([EchoTool()]))
    tool_port = ToolPortAdapter(executor, task_id=task_id, session_id=session_id_hint)

    runtime = _build_runtime(gateway, tool_port)
    driver = RuntimeDriver(runtime, config=DriverConfig(max_turns=1))

    result = driver.execute_task(
        task_id,
        requirements=[
            'Use the echo tool with the text "NEPTUNE_FULL_LOOP_OK". '
            "After receiving the tool result, respond with exactly: NEPTUNE_FULL_LOOP_DONE"
        ],
    )

    last_turn = result.turns_run[-1] if result.turns_run else None
    print(
        json.dumps(
            {
                "outcome": result.outcome.value,
                "turns_run": len(result.turns_run),
                "checkpoint_id": result.last_checkpoint.checkpoint_id if result.last_checkpoint else None,
                "last_turn_tool_calls": last_turn.tool_calls if last_turn else None,
            }
        )
    )


def do_resume_and_finish(task_id: str) -> None:
    gateway = FakeModelGateway(scripted_responses=[{"content": "NEPTUNE_FULL_LOOP_DONE", "tool_calls": []}])
    session_id_hint = f"{task_id}-session"
    executor = ToolExecutorService(ToolRegistryAdapter([EchoTool()]))
    tool_port = ToolPortAdapter(executor, task_id=task_id, session_id=session_id_hint)

    runtime = _build_runtime(gateway, tool_port)
    driver = RuntimeDriver(runtime)

    result = driver.execute_until_stop(task_id)

    print(
        json.dumps(
            {
                "outcome": result.outcome.value,
                "turns_run_this_call": len(result.turns_run),
                "final_task_status": result.task.status.value if result.task else None,
                "final_model_response": result.turns_run[-1].model_response if result.turns_run else None,
                "gateway_saw_recent_events": [
                    e.get("event_type") for e in gateway.requests_received[0].get("recent_events", [])
                ]
                if gateway.requests_received
                else [],
            }
        )
    )


if __name__ == "__main__":
    mode = sys.argv[1]
    task_id = sys.argv[2]
    if mode == "run_partial":
        do_run_partial(task_id)
    elif mode == "resume_and_finish":
        do_resume_and_finish(task_id)
    else:
        raise SystemExit(f"Unknown mode: {mode}")
