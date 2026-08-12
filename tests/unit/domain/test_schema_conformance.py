"""Gate 1: domain/schema conformance.

Validates that Task.to_dict() and Event.to_dict() output conforms to the
frozen 09_SCHEMAS/*.json schemas -- not just "looks right" but actually
validates against the schema Claude B and other consumers will rely on.
"""
from datetime import datetime, timezone

import jsonschema

from core.domain.event import Event
from core.domain.task import Task, TaskStatus


def test_task_to_dict_conforms_to_schema(task_schema):
    task = Task(
        task_id="task-001",
        status=TaskStatus.CREATED,
        created_at=datetime.now(timezone.utc),
        project_id="proj-1",
        requirements=["do the thing"],
        constraints={"max_turns": 10},
    )
    jsonschema.validate(instance=task.to_dict(), schema=task_schema)


def test_minimal_task_conforms_to_schema(task_schema):
    """Only the schema's required fields set; optional fields absent."""
    task = Task(task_id="task-002", status=TaskStatus.CREATED)
    payload = task.to_dict()
    jsonschema.validate(instance=payload, schema=task_schema)


def test_event_to_dict_conforms_to_schema(event_schema):
    event = Event(
        event_id="evt-001",
        event_type="task.created",
        task_id="task-001",
        timestamp=datetime.now(timezone.utc),
        actor="claude-a",
        payload={"reason": "initial creation"},
    )
    jsonschema.validate(instance=event.to_dict(), schema=event_schema)


def test_task_round_trip_preserves_identity():
    original = Task(
        task_id="task-003",
        status=TaskStatus.EXECUTING,
        parent_task_id="task-000",
        requirements=["a", "b"],
    )
    restored = Task.from_dict(original.to_dict())
    assert restored == original


def test_event_round_trip_preserves_identity():
    original = Event(
        event_id="evt-002",
        event_type="session.started",
        task_id="task-001",
        session_id="sess-1",
        agent_id="agent-1",
        payload={"k": "v"},
    )
    restored = Event.from_dict(original.to_dict())
    assert restored == original
