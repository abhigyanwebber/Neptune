"""Standalone script invoked as a SEPARATE OS process by
test_tool_execution_recovery.py (B-006).

Same pattern as _driver_recovery_script.py (A-005's own driver-level
recovery test), extended with a REAL ToolPort implementation --
ToolPortAdapter wrapping Neptune's ToolExecutorService/EchoTool
(B-004) -- instead of FakeToolPort, to prove that real tool execution
state survives a genuine process boundary via persisted checkpoint
state alone.

    python _tool_execution_recovery_script.py run_partial <task_id>
        -> RuntimeDriver runs exactly one turn (max_turns=1) against a
           gateway that always requests the real echo tool. The real
           EchoTool executes, its ToolResult is persisted as part of
           the Turn record (and as tool.requested/tool.observation_received
           Events), a checkpoint is recorded, and the process exits --
           simulating an interruption right after tool execution.
    python _tool_execution_recovery_script.py resume_and_finish <task_id>
        -> a brand-new process builds a fresh AgentRuntime + RuntimeDriver
           + a FRESH ToolPortAdapter/ToolExecutorService/EchoTool (no
           shared memory whatsoever with run_partial's instances), calls
           execute_until_stop(task_id), and this time the gateway returns
           a final response (tool_calls=[]) so the task completes on the
           very next turn without executing any tool again.
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
    # Always requests the real echo tool -- never a final response --
    # so the driver hits max_turns=1 right after the tool executes,
    # simulating an interruption immediately after tool execution.
    gateway = FakeModelGateway(
        default_response_fn=lambda req: {
            "content": "calling echo",
            "tool_calls": [{"tool_name": "echo", "args": {"text": "hello"}}],
        }
    )
    session_id_hint = f"{task_id}-session"
    executor = ToolExecutorService(ToolRegistryAdapter([EchoTool()]))
    tool_port = ToolPortAdapter(executor, task_id=task_id, session_id=session_id_hint)

    runtime = _build_runtime(gateway, tool_port)
    driver = RuntimeDriver(runtime, config=DriverConfig(max_turns=1))

    result = driver.execute_task(task_id, requirements=["echo hello via real tool execution"])

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
    # A brand-new process: no shared memory with do_run_partial's
    # runtime, driver, gateway, executor, or tool_port instances. Only
    # Postgres bridges the two. This gateway returns a final response
    # immediately, so the tool must NOT be requested again -- the only
    # thing this turn should do is complete the task.
    gateway = FakeModelGateway(
        scripted_responses=[{"content": "Done -- echo returned hello", "tool_calls": []}]
    )
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
                "checkpoint_id": result.last_checkpoint.checkpoint_id if result.last_checkpoint else None,
                "final_model_response": result.turns_run[-1].model_response if result.turns_run else None,
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
