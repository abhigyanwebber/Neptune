"""Checkpoint domain object.

Per 03_CONTRACTS/CHECKPOINT_CONTRACT.md: "a recoverable execution snapshot...
distinct from Git history." Invariant #3: "a checkpoint belongs to an
identifiable execution lineage" -- hence task_id is required while
session_id/agent_id are optional (a checkpoint may be task-level).
Snapshot contents/format are explicitly deferred by the contract, so `state`
is an opaque JSON payload defined by whatever created the checkpoint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Checkpoint:
    checkpoint_id: str
    task_id: str
    state: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    label: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "label": self.label,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            task_id=data["task_id"],
            session_id=data.get("session_id"),
            agent_id=data.get("agent_id"),
            label=data.get("label"),
            state=data.get("state") or {},
            created_at=_parse_dt(data["created_at"]),
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
