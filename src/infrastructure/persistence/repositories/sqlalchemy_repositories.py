"""SQLAlchemy implementations of the core repository contracts.

Each repository takes a `sessionmaker` and opens/commits one transaction per
call. This is a deliberately simple unit-of-work; SESSION_CONTRACT.md
defers "exact session persistence; concurrency model" so nothing here
should be read as final concurrency policy -- just a correct, minimal
Stage 1 baseline.

Only this module (and orm.py) may import SQLAlchemy. core/ never does.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession
from sqlalchemy.orm import sessionmaker

from core.domain.agent import Agent
from core.domain.checkpoint import Checkpoint
from core.domain.event import Event
from core.domain.session import Session as DomainSession
from core.domain.task import Task
from core.domain.turn import Turn

from ..models.orm import (
    AgentModel,
    CheckpointModel,
    EventModel,
    SessionModel,
    TaskModel,
    TurnModel,
)


class SqlAlchemyTaskRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, task: Task) -> None:
        with self._session_factory() as db:
            db.add(_task_to_model(task))
            db.commit()

    def get(self, task_id: str) -> Optional[Task]:
        with self._session_factory() as db:
            model = db.get(TaskModel, task_id)
            return _model_to_task(model) if model else None

    def update(self, task: Task) -> None:
        with self._session_factory() as db:
            model = db.get(TaskModel, task.task_id)
            if model is None:
                raise ValueError(f"Task not found: {task.task_id}")
            _apply_task_to_model(task, model)
            db.commit()

    def list_children(self, parent_task_id: str) -> list[Task]:
        with self._session_factory() as db:
            stmt = select(TaskModel).where(TaskModel.parent_task_id == parent_task_id)
            return [_model_to_task(m) for m in db.scalars(stmt)]


class SqlAlchemyAgentRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, agent: Agent) -> None:
        with self._session_factory() as db:
            db.add(_agent_to_model(agent))
            db.commit()

    def get(self, agent_id: str) -> Optional[Agent]:
        with self._session_factory() as db:
            model = db.get(AgentModel, agent_id)
            return _model_to_agent(model) if model else None

    def update(self, agent: Agent) -> None:
        with self._session_factory() as db:
            model = db.get(AgentModel, agent.agent_id)
            if model is None:
                raise ValueError(f"Agent not found: {agent.agent_id}")
            _apply_agent_to_model(agent, model)
            db.commit()

    def list_for_task(self, task_id: str) -> list[Agent]:
        with self._session_factory() as db:
            stmt = select(AgentModel).where(AgentModel.task_id == task_id)
            return [_model_to_agent(m) for m in db.scalars(stmt)]


class SqlAlchemySessionRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, session: DomainSession) -> None:
        with self._session_factory() as db:
            db.add(_session_to_model(session))
            db.commit()

    def get(self, session_id: str) -> Optional[DomainSession]:
        with self._session_factory() as db:
            model = db.get(SessionModel, session_id)
            return _model_to_session(model) if model else None

    def update(self, session: DomainSession) -> None:
        with self._session_factory() as db:
            model = db.get(SessionModel, session.session_id)
            if model is None:
                raise ValueError(f"Session not found: {session.session_id}")
            _apply_session_to_model(session, model)
            db.commit()

    def list_for_task(self, task_id: str) -> list[DomainSession]:
        with self._session_factory() as db:
            stmt = select(SessionModel).where(SessionModel.task_id == task_id)
            return [_model_to_session(m) for m in db.scalars(stmt)]


class SqlAlchemyTurnRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, turn: Turn) -> None:
        with self._session_factory() as db:
            db.add(_turn_to_model(turn))
            db.commit()

    def get(self, turn_id: str) -> Optional[Turn]:
        with self._session_factory() as db:
            model = db.get(TurnModel, turn_id)
            return _model_to_turn(model) if model else None

    def update(self, turn: Turn) -> None:
        with self._session_factory() as db:
            model = db.get(TurnModel, turn.turn_id)
            if model is None:
                raise ValueError(f"Turn not found: {turn.turn_id}")
            _apply_turn_to_model(turn, model)
            db.commit()

    def list_for_session(self, session_id: str) -> list[Turn]:
        with self._session_factory() as db:
            stmt = (
                select(TurnModel)
                .where(TurnModel.session_id == session_id)
                .order_by(TurnModel.sequence_number.asc())
            )
            return [_model_to_turn(m) for m in db.scalars(stmt)]


class SqlAlchemyEventRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def append(self, event: Event) -> None:
        with self._session_factory() as db:
            db.add(_event_to_model(event))
            db.commit()

    def get(self, event_id: str) -> Optional[Event]:
        with self._session_factory() as db:
            model = db.get(EventModel, event_id)
            return _model_to_event(model) if model else None

    def list_for_task(self, task_id: str) -> list[Event]:
        with self._session_factory() as db:
            stmt = (
                select(EventModel)
                .where(EventModel.task_id == task_id)
                .order_by(EventModel.timestamp.asc())
            )
            return [_model_to_event(m) for m in db.scalars(stmt)]


class SqlAlchemyCheckpointRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, checkpoint: Checkpoint) -> None:
        with self._session_factory() as db:
            db.add(_checkpoint_to_model(checkpoint))
            db.commit()

    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        with self._session_factory() as db:
            model = db.get(CheckpointModel, checkpoint_id)
            return _model_to_checkpoint(model) if model else None

    def list_for_task(self, task_id: str) -> list[Checkpoint]:
        with self._session_factory() as db:
            stmt = (
                select(CheckpointModel)
                .where(CheckpointModel.task_id == task_id)
                .order_by(CheckpointModel.created_at.asc())
            )
            return [_model_to_checkpoint(m) for m in db.scalars(stmt)]

    def latest_for_task(self, task_id: str) -> Optional[Checkpoint]:
        with self._session_factory() as db:
            stmt = (
                select(CheckpointModel)
                .where(CheckpointModel.task_id == task_id)
                .order_by(CheckpointModel.created_at.desc())
                .limit(1)
            )
            model = db.scalars(stmt).first()
            return _model_to_checkpoint(model) if model else None


# ---------------------------------------------------------------------------
# Conversion helpers (domain <-> ORM). Kept private and adjacent to the
# repositories that use them rather than on the domain objects, so the
# domain layer stays persistence-agnostic.
# ---------------------------------------------------------------------------

def _utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize a datetime read back from the DB to be timezone-aware UTC.

    Postgres's DateTime(timezone=True) round-trips tzinfo correctly, but
    SQLite (used in fast contract tests) silently returns naive datetimes.
    Domain equality (Task/Agent/... are frozen/eq dataclasses) must not
    depend on which dialect happens to be running underneath, so every
    ORM->domain conversion normalizes here rather than leaking a
    dialect-specific quirk into domain-level test assertions.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _task_to_model(t: Task) -> TaskModel:
    return TaskModel(
        task_id=t.task_id,
        parent_task_id=t.parent_task_id,
        project_id=t.project_id,
        status=t.status.value,
        constraints=t.constraints,
        requirements=t.requirements,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _apply_task_to_model(t: Task, m: TaskModel) -> None:
    m.parent_task_id = t.parent_task_id
    m.project_id = t.project_id
    m.status = t.status.value
    m.constraints = t.constraints
    m.requirements = t.requirements
    m.updated_at = t.updated_at


def _model_to_task(m: TaskModel) -> Task:
    return Task.from_dict(
        {
            "task_id": m.task_id,
            "parent_task_id": m.parent_task_id,
            "project_id": m.project_id,
            "status": m.status,
            "constraints": m.constraints,
            "requirements": m.requirements,
            "created_at": _utc(m.created_at),
            "updated_at": _utc(m.updated_at),
        }
    )


def _agent_to_model(a: Agent) -> AgentModel:
    return AgentModel(
        agent_id=a.agent_id,
        task_id=a.task_id,
        role=a.role,
        status=a.status.value,
        runtime_binding=a.runtime_binding,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _apply_agent_to_model(a: Agent, m: AgentModel) -> None:
    m.role = a.role
    m.status = a.status.value
    m.runtime_binding = a.runtime_binding
    m.updated_at = a.updated_at


def _model_to_agent(m: AgentModel) -> Agent:
    return Agent.from_dict(
        {
            "agent_id": m.agent_id,
            "task_id": m.task_id,
            "role": m.role,
            "status": m.status,
            "runtime_binding": m.runtime_binding,
            "created_at": _utc(m.created_at),
            "updated_at": _utc(m.updated_at),
        }
    )


def _session_to_model(s: DomainSession) -> SessionModel:
    return SessionModel(
        session_id=s.session_id,
        task_id=s.task_id,
        agent_id=s.agent_id,
        status=s.status.value,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _apply_session_to_model(s: DomainSession, m: SessionModel) -> None:
    m.status = s.status.value
    m.updated_at = s.updated_at


def _model_to_session(m: SessionModel) -> DomainSession:
    return DomainSession.from_dict(
        {
            "session_id": m.session_id,
            "task_id": m.task_id,
            "agent_id": m.agent_id,
            "status": m.status,
            "created_at": _utc(m.created_at),
            "updated_at": _utc(m.updated_at),
        }
    )


def _turn_to_model(t: Turn) -> TurnModel:
    return TurnModel(
        turn_id=t.turn_id,
        session_id=t.session_id,
        sequence_number=t.sequence_number,
        status=t.status.value,
        model_request=t.model_request,
        model_response=t.model_response,
        tool_calls=t.tool_calls,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _apply_turn_to_model(t: Turn, m: TurnModel) -> None:
    m.status = t.status.value
    m.model_request = t.model_request
    m.model_response = t.model_response
    m.tool_calls = t.tool_calls
    m.updated_at = t.updated_at


def _model_to_turn(m: TurnModel) -> Turn:
    return Turn.from_dict(
        {
            "turn_id": m.turn_id,
            "session_id": m.session_id,
            "sequence_number": m.sequence_number,
            "status": m.status,
            "model_request": m.model_request,
            "model_response": m.model_response,
            "tool_calls": m.tool_calls,
            "created_at": _utc(m.created_at),
            "updated_at": _utc(m.updated_at),
        }
    )


def _event_to_model(e: Event) -> EventModel:
    return EventModel(
        event_id=e.event_id,
        event_type=e.event_type,
        task_id=e.task_id,
        session_id=e.session_id,
        agent_id=e.agent_id,
        actor=e.actor,
        payload=e.payload,
        correlation_id=e.correlation_id,
        provenance=e.provenance,
        security=e.security,
        timestamp=e.timestamp,
    )


def _model_to_event(m: EventModel) -> Event:
    return Event.from_dict(
        {
            "event_id": m.event_id,
            "event_type": m.event_type,
            "task_id": m.task_id,
            "session_id": m.session_id,
            "agent_id": m.agent_id,
            "actor": m.actor,
            "payload": m.payload,
            "correlation_id": m.correlation_id,
            "provenance": m.provenance,
            "security": m.security,
            "timestamp": _utc(m.timestamp),
        }
    )


def _checkpoint_to_model(c: Checkpoint) -> CheckpointModel:
    return CheckpointModel(
        checkpoint_id=c.checkpoint_id,
        task_id=c.task_id,
        session_id=c.session_id,
        agent_id=c.agent_id,
        label=c.label,
        state=c.state,
        created_at=c.created_at,
    )


def _model_to_checkpoint(m: CheckpointModel) -> Checkpoint:
    return Checkpoint.from_dict(
        {
            "checkpoint_id": m.checkpoint_id,
            "task_id": m.task_id,
            "session_id": m.session_id,
            "agent_id": m.agent_id,
            "label": m.label,
            "state": m.state,
            "created_at": _utc(m.created_at),
        }
    )
