"""Turn domain object.

Per 02_ARCHITECTURE/06_CORE_DOMAIN_MODEL.md: "one model/tool interaction
cycle within a session... not necessarily identical to a single model API
request because tool loops may involve multiple tool operations before the
next model response." We record the turn as a durable envelope; the actual
model request/response and tool-call payloads are stored as structured JSON
(sequence unspecified deliberately -- Model Gateway/tool system land later).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class TurnStatus(str, Enum):
    STARTED = "started"
    AWAITING_MODEL = "awaiting_model"
    AWAITING_TOOL = "awaiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Turn:
    turn_id: str
    session_id: str
    sequence_number: int
    status: TurnStatus = TurnStatus.STARTED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model_request: Optional[dict[str, Any]] = None
    model_response: Optional[dict[str, Any]] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "sequence_number": self.sequence_number,
            "status": self.status.value,
            "model_request": self.model_request,
            "model_response": self.model_response,
            "tool_calls": self.tool_calls,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Turn":
        return cls(
            turn_id=data["turn_id"],
            session_id=data["session_id"],
            sequence_number=data["sequence_number"],
            status=TurnStatus(data["status"]),
            model_request=data.get("model_request"),
            model_response=data.get("model_response"),
            tool_calls=data.get("tool_calls") or [],
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]) if data.get("updated_at") else None,
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
