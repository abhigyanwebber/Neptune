"""Unit-level test of the Core Agent Runtime lifecycle, using SQLite (fast,
no Docker) and the Fake Model Gateway / Fake Tool Port test doubles.

Walks through success criteria 1-11 from the director's brief:
create task -> start agent run -> start session -> run turn (model
request/response) -> tool request/observation -> next turn -> events
persisted -> checkpoint.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from core.domain.agent import AgentStatus
from core.domain.task import TaskStatus
from core.domain.turn import TurnStatus
from core.runtime.engine import AgentRuntime
from core.runtime.fakes import FakeModelGateway, FakeToolPort
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyAgentRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyTurnRepository,
)


@pytest.fixture()
def runtime():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    gateway = FakeModelGateway(
        scripted_responses=[
            {
                "content": "I'll check the file first.",
                "tool_calls": [{"tool_name": "read_file", "args": {"path": "README.md"}}],
            },
            {"content": "Looks good, done.", "tool_calls": []},
        ]
    )
    tools = FakeToolPort()

    rt = AgentRuntime(
        task_repo=SqlAlchemyTaskRepository(sf),
        agent_repo=SqlAlchemyAgentRepository(sf),
        session_repo=SqlAlchemySessionRepository(sf),
        turn_repo=SqlAlchemyTurnRepository(sf),
        event_repo=SqlAlchemyEventRepository(sf),
        checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
        model_gateway=gateway,
        tool_port=tools,
    )
    return rt, gateway, tools, SqlAlchemyEventRepository(sf)


def test_full_lifecycle_through_checkpoint(runtime):
    rt, gateway, tools, events = runtime

    # 1. Create task
    task = rt.create_task("task-1", requirements=["implement feature X"])
    assert task.status == TaskStatus.CREATED

    # 2. Start agent run (also advances task into EXECUTING)
    agent = rt.start_agent_run("task-1", role="core-implementer")
    assert agent.status == AgentStatus.ACTIVE

    # 3. Start session
    session = rt.start_session("task-1", agent.agent_id)

    # 4-8. Turn 1: model responds with a tool call; tool executes; observed
    turn1 = rt.run_turn(session.session_id)
    assert turn1.sequence_number == 1
    assert turn1.status == TurnStatus.COMPLETED
    assert turn1.model_request is not None
    assert turn1.model_response["content"] == "I'll check the file first."
    assert len(turn1.tool_calls) == 1
    assert turn1.tool_calls[0]["observation"]["tool_name"] == "read_file"
    assert tools.calls_received[0]["tool_name"] == "read_file"

    # 9. Continue to next turn (no tool calls this time)
    turn2 = rt.run_turn(session.session_id)
    assert turn2.sequence_number == 2
    assert turn2.tool_calls == []

    # 10. Events persisted for every lifecycle step
    task_events = events.list_for_task("task-1")
    event_types = [e.event_type for e in task_events]
    assert "task.created" in event_types
    assert "agent_run.started" in event_types
    assert "session.started" in event_types
    assert event_types.count("turn.started") == 2
    assert event_types.count("model.response_received") == 2
    assert "tool.requested" in event_types
    assert "tool.observation_received" in event_types
    assert event_types.count("turn.completed") == 2

    # 11. Checkpoint
    cp = rt.checkpoint("task-1", session.session_id, agent.agent_id, label="after-turn-2")
    assert cp.state["last_turn_id"] == turn2.turn_id
    assert cp.state["last_sequence_number"] == 2
    assert cp.state["task_status"] == "executing"

    assert len(gateway.requests_received) == 2


def test_run_turn_on_missing_session_raises(runtime):
    rt, *_ = runtime
    from core.runtime.errors import IllegalRuntimeTransition

    with pytest.raises(IllegalRuntimeTransition):
        rt.run_turn("nonexistent-session")


def test_complete_task_transitions_through_verifying(runtime):
    rt, *_ = runtime
    rt.create_task("task-2")
    rt.start_agent_run("task-2", role="core-implementer")
    task = rt.complete_task("task-2")
    assert task.status == TaskStatus.COMPLETED
