"""Standalone script invoked as a SEPARATE OS process by
test_driver_recovery.py.

    python _driver_recovery_script.py run_partial <task_id>
        -> RuntimeDriver drives a task with a gateway that never returns a
           final response (max_turns=2), so execution stops via
           STOPPED_MAX_TURNS with a checkpoint recorded after each turn.
           Process exits.
    python _driver_recovery_script.py resume_and_finish <task_id>
        -> a brand-new process builds a fresh AgentRuntime + RuntimeDriver,
           calls execute_until_stop(task_id) with a gateway that now
           returns a final response on the very next turn, completing the
           task. This proves checkpoint + resume works at the DRIVER
           level (not just the runtime level, which Stage 2 already
           covers), across a genuine process boundary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from config.settings import get_database_url  # noqa: E402
from core.runtime.driver import DriverConfig, DriverOutcome, RuntimeDriver  # noqa: E402
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


def do_run_partial(task_id: str) -> None:
    # Never returns a final (tool_calls == []) response -- forces the
    # driver to hit max_turns and stop mid-execution, exactly like a real
    # long-running task interrupted by a process restart.
    gateway = FakeModelGateway(
        default_response_fn=lambda req: {
            "content": "still working",
            "tool_calls": [{"tool_name": "read_file", "args": {}}],
        }
    )
    runtime = _build_runtime(gateway, FakeToolPort())
    driver = RuntimeDriver(runtime, config=DriverConfig(max_turns=2))

    result = driver.execute_task(task_id, requirements=["multi-turn recoverable work"])

    print(
        json.dumps(
            {
                "outcome": result.outcome.value,
                "turns_run": len(result.turns_run),
                "checkpoint_id": result.last_checkpoint.checkpoint_id if result.last_checkpoint else None,
            }
        )
    )


def do_resume_and_finish(task_id: str) -> None:
    # A brand-new process: no shared memory with do_run_partial's runtime,
    # driver, or gateway instances. Only Postgres bridges the two. This
    # gateway DOES return a final response, so resuming should complete
    # the task on the very next turn.
    gateway = FakeModelGateway(scripted_responses=[{"content": "finishing up", "tool_calls": []}])
    runtime = _build_runtime(gateway, FakeToolPort())
    driver = RuntimeDriver(runtime)

    result = driver.execute_until_stop(task_id)

    print(
        json.dumps(
            {
                "outcome": result.outcome.value,
                "turns_run_this_call": len(result.turns_run),
                "final_task_status": result.task.status.value if result.task else None,
                "checkpoint_id": result.last_checkpoint.checkpoint_id if result.last_checkpoint else None,
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
