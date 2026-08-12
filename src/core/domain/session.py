"""Session domain object.

Per 03_CONTRACTS/SESSION_CONTRACT.md: "a resumable execution boundary for an
agent working on a task." Invariant #3 there ("session identity survives
model/provider switching") is why this object carries no provider/model
fields -- those belong to the Model Gateway (Claude B's lane), attributed to
sessions only indirectly through Turn/Event records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Session:
    session_id: str
    task_id: str
    agent_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            session_id=data["session_id"],
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            status=SessionStatus(data["status"]),
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]) if data.get("updated_at") else None,
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
