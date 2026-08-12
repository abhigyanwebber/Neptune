"""Standalone script invoked as a SEPARATE OS process by test_recovery.py.

Run as:
    python _recovery_script.py write   -> creates task/session/turn/event/
                                           checkpoint, prints checkpoint_id,
                                           then this process exits (dies).
    python _recovery_script.py read <task_id>
                                        -> a brand-new process reconnects
                                           and prints recovered state as
                                           JSON. No in-memory state from the
                                           write run is available to it.

This is the literal "create -> checkpoint -> terminate process -> restart
-> recover state" proof the director asked for, not just a fresh in-memory
object in the same test process.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from core.domain.agent import Agent  # noqa: E402
from core.domain.checkpoint import Checkpoint  # noqa: E402
from core.domain.event import Event  # noqa: E402
from core.domain.session import Session as DomainSession  # noqa: E402
from core.domain.task import Task, TaskStatus  # noqa: E402
from core.domain.turn import Turn  # noqa: E402
from config.settings import get_database_url  # noqa: E402
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


def _repos():
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return (
        SqlAlchemyTaskRepository(sf),
        SqlAlchemyAgentRepository(sf),
        SqlAlchemySessionRepository(sf),
        SqlAlchemyTurnRepository(sf),
        SqlAlchemyEventRepository(sf),
        SqlAlchemyCheckpointRepository(sf),
    )


def do_write(task_id: str) -> None:
    tasks, agents, sessions, turns, events, checkpoints = _repos()

    task = Task(task_id=task_id, status=TaskStatus.CREATED)
    tasks.create(task)
    task.transition_to(TaskStatus.QUEUED)
    task.transition_to(TaskStatus.PLANNING)
    task.transition_to(TaskStatus.EXECUTING)
    tasks.update(task)

    agent = Agent(agent_id=f"{task_id}-agent", task_id=task_id, role="core-implementer")
    agents.create(agent)

    session = DomainSession(session_id=f"{task_id}-session", task_id=task_id, agent_id=agent.agent_id)
    sessions.create(session)

    turn = Turn(turn_id=f"{task_id}-turn-1", session_id=session.session_id, sequence_number=1)
    turns.create(turn)

    events.append(
        Event(
            event_id=f"{task_id}-evt-1",
            event_type="task.executing",
            task_id=task_id,
            session_id=session.session_id,
            agent_id=agent.agent_id,
            actor="claude-a-recovery-script",
            payload={"note": "recovery test write phase"},
        )
    )

    checkpoint = Checkpoint(
        checkpoint_id=f"{task_id}-checkpoint-1",
        task_id=task_id,
        session_id=session.session_id,
        agent_id=agent.agent_id,
        label="recovery-test",
        state={"task_status": task.status.value, "last_turn": turn.turn_id},
    )
    checkpoints.create(checkpoint)

    print(json.dumps({"checkpoint_id": checkpoint.checkpoint_id}))


def do_read(task_id: str) -> None:
    tasks, agents, sessions, turns, events, checkpoints = _repos()

    task = tasks.get(task_id)
    agent = agents.get(f"{task_id}-agent")
    session = sessions.get(f"{task_id}-session")
    task_turns = turns.list_for_session(f"{task_id}-session")
    task_events = events.list_for_task(task_id)
    latest_checkpoint = checkpoints.latest_for_task(task_id)

    result = {
        "task": task.to_dict() if task else None,
        "agent": agent.to_dict() if agent else None,
        "session": session.to_dict() if session else None,
        "turn_count": len(task_turns),
        "event_count": len(task_events),
        "latest_checkpoint": latest_checkpoint.to_dict() if latest_checkpoint else None,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    mode = sys.argv[1]
    task_id = sys.argv[2]
    if mode == "write":
        do_write(task_id)
    elif mode == "read":
        do_read(task_id)
    else:
        raise SystemExit(f"Unknown mode: {mode}")
