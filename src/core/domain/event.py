"""Event domain object.

Mirrors 09_SCHEMAS/event.schema.json exactly. Events are immutable records
of significant occurrences and provide operational history / audit trail
(02_ARCHITECTURE/06_CORE_DOMAIN_MODEL.md). Append-only by design: there is
deliberately no update path on this object or its repository.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    task_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    actor: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    provenance: dict[str, Any] = field(default_factory=dict)
    security: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "task_id": self.task_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "actor": self.actor,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "provenance": self.provenance,
            "security": self.security,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            task_id=data["task_id"],
            timestamp=_parse_dt(data["timestamp"]),
            session_id=data.get("session_id"),
            agent_id=data.get("agent_id"),
            actor=data.get("actor"),
            payload=data.get("payload") or {},
            correlation_id=data.get("correlation_id"),
            provenance=data.get("provenance") or {},
            security=data.get("security") or {},
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
