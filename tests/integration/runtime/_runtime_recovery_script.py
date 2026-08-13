"""Standalone script invoked as a SEPARATE OS process by test_runtime_recovery.py.

    python _runtime_recovery_script.py write <task_id>
        -> full lifecycle through checkpoint (using fakes for gateway/tool),
           then this process exits (dies).
    python _runtime_recovery_script.py resume <task_id>
        -> a brand-new process constructs a NEW AgentRuntime, calls
           .resume(task_id), continues with one more turn, then completes
           the task. Prints the final state as JSON.

This proves resume/recovery at the RUNTIME level (not just repository
level, which tests/integration/persistence/test_recovery.py already
covers): a second, unrelated process must be able to reconstruct where
execution left off purely from Postgres and continue driving the loop.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from config.settings import get_database_url  # noqa: E402
from core.runtime.engine import AgentRuntime  # noqa: E402
from core.runtime.fakes import FakeModelGateway, FakeToolPort  # noqa: E402
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


def _build_runtime(gateway, tools) -> AgentRuntime:
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
        tool_port=tools,
    )


def do_write(task_id: str) -> None:
    gateway = FakeModelGateway(
        scripted_responses=[
            {"content": "starting work", "tool_calls": [{"tool_name": "read_file", "args": {}}]},
        ]
    )
    rt = _build_runtime(gateway, FakeToolPort())

    rt.create_task(task_id, requirements=["do the recoverable thing"])
    agent = rt.start_agent_run(task_id, role="core-implementer")
    session = rt.start_session(task_id, agent.agent_id)
    turn = rt.run_turn(session.session_id)
    cp = rt.checkpoint(task_id, session.session_id, agent.agent_id, label="mid-execution")

    print(
        json.dumps(
            {
                "agent_id": agent.agent_id,
                "session_id": session.session_id,
                "turn_id": turn.turn_id,
                "checkpoint_id": cp.checkpoint_id,
            }
        )
    )


def do_resume(task_id: str) -> None:
    # A brand-new process: no shared memory with do_write's runtime, gateway,
    # or repository instances. Only Postgres bridges the two.
    gateway = FakeModelGateway(scripted_responses=[{"content": "finishing up", "tool_calls": []}])
    rt = _build_runtime(gateway, FakeToolPort())

    state = rt.resume(task_id)
    assert state.active_session is not None, "no active session recovered"

    next_turn = rt.run_turn(state.active_session.session_id)
    completed_task = rt.complete_task(task_id)

    print(
        json.dumps(
            {
                "recovered_task_status_before_resume": state.task.status.value,
                "recovered_turn_count": len(state.turns),
                "recovered_latest_checkpoint_id": (
                    state.latest_checkpoint.checkpoint_id if state.latest_checkpoint else None
                ),
                "next_turn_sequence_number": next_turn.sequence_number,
                "final_task_status": completed_task.status.value,
            }
        )
    )


if __name__ == "__main__":
    mode = sys.argv[1]
    task_id = sys.argv[2]
    if mode == "write":
        do_write(task_id)
    elif mode == "resume":
        do_resume(task_id)
    else:
        raise SystemExit(f"Unknown mode: {mode}")
