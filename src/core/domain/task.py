"""Task domain object.

Mirrors 09_SCHEMAS/task.schema.json exactly. Task is a durable unit of
requested work; it may have parent/child relationships and may be executed
by one or more agent sessions over time (02_ARCHITECTURE/06_CORE_DOMAIN_MODEL.md).

This module has zero infrastructure/provider imports (provider independence
of the core, per Bible 02_ARCHITECTURE/02_DEPENDENCY_DIRECTION.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


# Statuses a task may transition into from a given status. Enforced by
# Task.transition_to() so illegal lifecycle jumps fail fast in the domain
# layer rather than silently persisting.
_ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.CREATED: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.PLANNING, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {TaskStatus.EXECUTING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.EXECUTING: {
        TaskStatus.VERIFYING,
        TaskStatus.PAUSED,
        TaskStatus.SUSPENDED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.VERIFYING: {TaskStatus.COMPLETED, TaskStatus.EXECUTING, TaskStatus.FAILED},
    TaskStatus.PAUSED: {TaskStatus.EXECUTING, TaskStatus.CANCELLED},
    TaskStatus.SUSPENDED: {TaskStatus.EXECUTING, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: {TaskStatus.QUEUED},
    TaskStatus.CANCELLED: set(),
}


@dataclass
class Task:
    task_id: str
    status: TaskStatus = TaskStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_task_id: Optional[str] = None
    project_id: Optional[str] = None
    constraints: dict[str, Any] = field(default_factory=dict)
    requirements: list[str] = field(default_factory=list)
    updated_at: Optional[datetime] = None

    def transition_to(self, new_status: TaskStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Illegal task transition: {self.status.value} -> {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        # task.schema.json declares updated_at as {"type": "string",
        # "format": "date-time"} with no "null" option (unlike
        # parent_task_id/project_id, which explicitly allow null) -- so an
        # unset updated_at must be omitted, not emitted as null.
        payload: dict[str, Any] = {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "constraints": self.constraints,
            "requirements": self.requirements,
            "created_at": self.created_at.isoformat(),
        }
        if self.updated_at is not None:
            payload["updated_at"] = self.updated_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            task_id=data["task_id"],
            parent_task_id=data.get("parent_task_id"),
            project_id=data.get("project_id"),
            status=TaskStatus(data["status"]),
            constraints=data.get("constraints") or {},
            requirements=data.get("requirements") or [],
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]) if data.get("updated_at") else None,
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
