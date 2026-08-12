"""Gate 2 (part 1): repository contract behavior.

Runs the SQLAlchemy repository implementations against an in-memory SQLite
engine. This validates *behavior* (create/get/update/list, ordering
invariants, append-only events) independent of the concrete production
database -- fast, no Docker required. The Postgres-specific process-death
recovery test lives separately in tests/integration/persistence, since that
one is about surviving a real process restart, not general contract shape.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine

from core.domain.agent import Agent, AgentStatus
from core.domain.checkpoint import Checkpoint
from core.domain.event import Event
from core.domain.session import Session as DomainSession
from core.domain.session import SessionStatus
from core.domain.task import Task, TaskStatus
from core.domain.turn import Turn, TurnStatus
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyAgentRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyTurnRepository,
)


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    return make_session_factory(engine)


def test_task_repository_create_get_update(session_factory):
    repo = SqlAlchemyTaskRepository(session_factory)
    task = Task(task_id="t1", status=TaskStatus.CREATED)
    repo.create(task)

    fetched = repo.get("t1")
    assert fetched == task

    task.transition_to(TaskStatus.QUEUED)
    repo.update(task)
    assert repo.get("t1").status == TaskStatus.QUEUED
    assert repo.get("missing") is None


def test_task_repository_list_children(session_factory):
    repo = SqlAlchemyTaskRepository(session_factory)
    parent = Task(task_id="parent", status=TaskStatus.CREATED)
    child1 = Task(task_id="child1", status=TaskStatus.CREATED, parent_task_id="parent")
    child2 = Task(task_id="child2", status=TaskStatus.CREATED, parent_task_id="parent")
    for t in (parent, child1, child2):
        repo.create(t)

    children = {t.task_id for t in repo.list_children("parent")}
    assert children == {"child1", "child2"}


def test_agent_repository_roundtrip(session_factory):
    SqlAlchemyTaskRepository(session_factory).create(Task(task_id="t1", status=TaskStatus.CREATED))
    repo = SqlAlchemyAgentRepository(session_factory)
    agent = Agent(agent_id="a1", task_id="t1", role="core-implementer")
    repo.create(agent)

    assert repo.get("a1") == agent
    agent.status = AgentStatus.ACTIVE
    repo.update(agent)
    assert repo.get("a1").status == AgentStatus.ACTIVE
    assert [a.agent_id for a in repo.list_for_task("t1")] == ["a1"]


def test_turn_repository_orders_by_sequence_number(session_factory):
    SqlAlchemyTaskRepository(session_factory).create(Task(task_id="t1", status=TaskStatus.CREATED))
    SqlAlchemyAgentRepository(session_factory).create(
        Agent(agent_id="a1", task_id="t1", role="core-implementer")
    )
    SqlAlchemySessionRepository(session_factory).create(
        DomainSession(session_id="s1", task_id="t1", agent_id="a1")
    )
    turn_repo = SqlAlchemyTurnRepository(session_factory)

    # Insert out of order on purpose.
    turn_repo.create(Turn(turn_id="turn-3", session_id="s1", sequence_number=3))
    turn_repo.create(Turn(turn_id="turn-1", session_id="s1", sequence_number=1))
    turn_repo.create(Turn(turn_id="turn-2", session_id="s1", sequence_number=2))

    ordered = turn_repo.list_for_session("s1")
    assert [t.sequence_number for t in ordered] == [1, 2, 3]


def test_event_repository_is_append_only_and_ordered(session_factory):
    SqlAlchemyTaskRepository(session_factory).create(Task(task_id="t1", status=TaskStatus.CREATED))
    repo = SqlAlchemyEventRepository(session_factory)

    # No update()/delete() method exists on the repository at all -- this
    # assertion documents that append-only-ness, rather than merely testing
    # ordering.
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")

    base = datetime.now(timezone.utc)
    repo.append(Event(event_id="e2", event_type="x", task_id="t1", timestamp=base + timedelta(seconds=2)))
    repo.append(Event(event_id="e1", event_type="x", task_id="t1", timestamp=base + timedelta(seconds=1)))

    ordered = repo.list_for_task("t1")
    assert [e.event_id for e in ordered] == ["e1", "e2"]


def test_checkpoint_repository_latest_for_task(session_factory):
    SqlAlchemyTaskRepository(session_factory).create(Task(task_id="t1", status=TaskStatus.CREATED))
    repo = SqlAlchemyCheckpointRepository(session_factory)

    base = datetime.now(timezone.utc)
    repo.create(Checkpoint(checkpoint_id="c1", task_id="t1", created_at=base))
    repo.create(Checkpoint(checkpoint_id="c2", task_id="t1", created_at=base + timedelta(seconds=5)))

    latest = repo.latest_for_task("t1")
    assert latest.checkpoint_id == "c2"
