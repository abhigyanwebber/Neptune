"""Minimal context assembly.

Deliberately NOT full context engineering (repository indexing, memory
retrieval, prompt templating) -- the director brief explicitly excludes
that from this stage ("Do not implement... full context/repository
indexing"). This assembles just enough structured information for a
Model Gateway request to be meaningful: task requirements/constraints,
session identity, and recent event history for continuity across turns.
"""
from __future__ import annotations

from typing import Any

from core.domain.event import Event
from core.domain.session import Session
from core.domain.task import Task


def assemble_context(task: Task, session: Session, recent_events: list[Event]) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "session_id": session.session_id,
        "agent_id": session.agent_id,
        "task_status": task.status.value,
        "requirements": task.requirements,
        "constraints": task.constraints,
        "recent_events": [
            {"event_type": e.event_type, "payload": e.payload} for e in recent_events
        ],
    }
