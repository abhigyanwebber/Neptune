"""SQLAlchemy ORM table definitions.

Deliberately kept separate from core/domain -- these are persistence
mapping details (Bible 06_CORE_DOMAIN_MODEL.md: "not a database schema").
Nothing in core/ imports this module; only infrastructure/persistence
repositories do.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TaskModel(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    project_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_tasks_parent_task_id", "parent_task_id"),)


class AgentModel(Base):
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    runtime_binding: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_agents_task_id", "task_id"),)


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_sessions_task_id", "task_id"),
        Index("ix_sessions_agent_id", "agent_id"),
    )


class TurnModel(Base):
    __tablename__ = "turns"

    turn_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.session_id"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    model_request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_turns_session_id_sequence", "session_id", "sequence_number", unique=True),
    )


class EventModel(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    # NOT a ForeignKey to tasks.task_id (deliberately, as of A-004). The
    # frozen event.schema.json requires task_id to be a string, not that
    # it reference an existing Task row -- e.g. registry audit events
    # (core/registry/audit.py) use a sentinel "system-registry" task_id
    # for events that aren't scoped to any real Task. An earlier version
    # of this column had a ForeignKey constraint; it worked on SQLite
    # (constraints unenforced there by default) but broke on Postgres
    # (constraints enforced) the first time a non-task-scoped event was
    # written. See ADR-A-010.
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    security: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_events_task_id_timestamp", "task_id", "timestamp"),
    )


class PlanModel(Base):
    __tablename__ = "plans"

    plan_id: Mapped[str] = mapped_column(String, primary_key=True)
    goal_id: Mapped[str] = mapped_column(String, nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_plans_goal_id", "goal_id"),)


class CapabilityModel(Base):
    __tablename__ = "capabilities"

    capability_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_date: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_source: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_checked: Mapped[str | None] = mapped_column(String, nullable=True)


class ProviderModel(Base):
    __tablename__ = "providers"

    provider_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    provider_type: Mapped[str] = mapped_column(String, nullable=False)
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, nullable=False)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)
    verification_date: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_source: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_checked: Mapped[str | None] = mapped_column(String, nullable=True)


class ResourceModel(Base):
    __tablename__ = "resources"

    resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    criticality: Mapped[str] = mapped_column(String, nullable=False)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)
    verification_date: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_source: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_checked: Mapped[str | None] = mapped_column(String, nullable=True)


class ToolDefinitionModel(Base):
    __tablename__ = "tool_definitions"

    tool_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    capability: Mapped[str] = mapped_column(String, nullable=False)
    risk_class: Mapped[str | None] = mapped_column(String, nullable=True)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)
    verification_date: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_source: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_checked: Mapped[str | None] = mapped_column(String, nullable=True)


class CheckpointModel(Base):
    __tablename__ = "checkpoints"

    checkpoint_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_checkpoints_task_id_created_at", "task_id", "created_at"),
    )
