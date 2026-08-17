"""Agent domain object.

An Agent is a runtime actor assigned to perform work on a Task. Per
02_ARCHITECTURE/06_CORE_DOMAIN_MODEL.md, an Agent "has a role and a runtime
binding, but does not own provider infrastructure or project policy" -- so
this object intentionally has no model/provider fields. Model selection is
Claude B's Model Gateway concern (out of scope here).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AgentStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Agent:
    agent_id: str
    task_id: str
    role: str
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    runtime_binding: dict[str, Any] = field(default_factory=dict)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "role": self.role,
            "status": self.status.value,
            "runtime_binding": self.runtime_binding,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Agent":
        return cls(
            agent_id=data["agent_id"],
            task_id=data["task_id"],
            role=data["role"],
            status=AgentStatus(data["status"]),
            runtime_binding=data.get("runtime_binding") or {},
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]) if data.get("updated_at") else None,
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
