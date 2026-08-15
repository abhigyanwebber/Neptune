"""Registry audit trail: reuses the existing Event infrastructure (no new
event system, per task A-004 instruction).

Registry mutations aren't scoped to any Task -- but event.schema.json
(FROZEN) requires task_id on every Event. Rather than weakening that
frozen contract, registry audit events use a well-known sentinel task_id
so they still flow through the same EventRepository/Event pipeline every
other part of Neptune uses. This is an implementation decision, not a
contract change -- see ADR-A-010.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from core.domain.event import Event

if TYPE_CHECKING:  # pragma: no cover
    from core.contracts.repositories import EventRepository

# Sentinel task_id for registry-scoped (non-task-scoped) audit events.
# Never a real Task -- nothing should ever create a Task with this id.
SYSTEM_REGISTRY_TASK_ID = "system-registry"

ACTOR = "core-registry"


def emit_registry_event(
    event_repo: Optional["EventRepository"],
    event_type: str,
    entity_id: str,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    """No-op if event_repo is None -- audit emission is optional so the
    registries remain usable (e.g. in tests) without wiring an
    EventRepository."""
    if event_repo is None:
        return
    event_repo.append(
        Event(
            event_id=f"evt-{uuid.uuid4().hex}",
            event_type=event_type,
            task_id=SYSTEM_REGISTRY_TASK_ID,
            actor=ACTOR,
            payload={"entity_id": entity_id, **(payload or {})},
            timestamp=datetime.now(timezone.utc),
        )
    )
