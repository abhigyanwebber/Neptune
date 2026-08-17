"""Core Agent Runtime -- the control-plane orchestrator.

Implements the target lifecycle:

    Task -> Agent Run -> Session -> Context -> Model Request -> Tool
    Request -> Observation -> Event -> Checkpoint -> Continue / Complete
    / Recover

This module has zero provider/infrastructure imports. It depends only on:
- core.domain (plain dataclasses)
- core.contracts (repository Protocols + ModelGatewayPort + ToolPort)

Claude B's real Model Gateway and Tool/Permission layer satisfy
ModelGatewayPort / ToolPort structurally; FakeModelGateway / FakeToolPort
in fakes.py let this engine run fully without either (director brief:
"The Core must be testable without a real provider").

State-machine scope (director warning acknowledged): this stage does NOT
introduce a large frozen transition-rule library for Agent/Session/Turn.
Task already has one (from Stage 0/1) because task.schema.json's status
enum made that requirement explicit. Agent/Session/Turn status changes here
are the minimum the lifecycle above actually needs, enforced procedurally
in this engine rather than as a separate generalized rule table -- see
ADR note in DEVELOPMENT_STATE/decisions.yaml (ADR-A-004).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from core.contracts.gateway import ModelGatewayPort
from core.contracts.repositories import (
    AgentRepository,
    CheckpointRepository,
    EventRepository,
    SessionRepository,
    TaskRepository,
    TurnRepository,
)
from core.contracts.tools import ToolPort
from core.domain.agent import Agent, AgentStatus
from core.domain.checkpoint import Checkpoint
from core.domain.event import Event
from core.domain.session import Session, SessionStatus
from core.domain.task import Task, TaskStatus
from core.domain.turn import Turn, TurnStatus

from .context import assemble_context
from .errors import IllegalRuntimeTransition

# Turns end once the model returns a response with no further tool calls.
# Safety ceiling only -- not a policy decision; prevents a runaway loop
# from a misbehaving fake/gateway during tests/dev.
_MAX_TOOL_ROUNDS_PER_TURN = 25


class AgentRuntime:
    def __init__(
        self,
        task_repo: TaskRepository,
        agent_repo: AgentRepository,
        session_repo: SessionRepository,
        turn_repo: TurnRepository,
        event_repo: EventRepository,
        checkpoint_repo: CheckpointRepository,
        model_gateway: ModelGatewayPort,
        tool_port: ToolPort,
    ) -> None:
        self._tasks = task_repo
        self._agents = agent_repo
        self._sessions = session_repo
        self._turns = turn_repo
        self._events = event_repo
        self._checkpoints = checkpoint_repo
        self._gateway = model_gateway
        self._tools = tool_port

    # ------------------------------------------------------------------
    # 1. Task
    # ------------------------------------------------------------------
    def create_task(
        self,
        task_id: str,
        requirements: Optional[list[str]] = None,
        constraints: Optional[dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> Task:
        task = Task(
            task_id=task_id,
            status=TaskStatus.CREATED,
            requirements=requirements or [],
            constraints=constraints or {},
            project_id=project_id,
        )
        self._tasks.create(task)
        self._emit("task.created", task_id=task_id, payload={"requirements": task.requirements})
        return task

    # ------------------------------------------------------------------
    # 2. Agent Run
    # ------------------------------------------------------------------
    def start_agent_run(self, task_id: str, role: str, agent_id: Optional[str] = None) -> Agent:
        task = self._require_task(task_id)
        if task.status == TaskStatus.CREATED:
            task.transition_to(TaskStatus.QUEUED)
            task.transition_to(TaskStatus.PLANNING)
            task.transition_to(TaskStatus.EXECUTING)
            self._tasks.update(task)

        agent = Agent(agent_id=agent_id or f"{task_id}-agent-{_short_id()}", task_id=task_id, role=role)
        agent.status = AgentStatus.ACTIVE
        self._agents.create(agent)
        self._emit(
            "agent_run.started",
            task_id=task_id,
            agent_id=agent.agent_id,
            payload={"role": role},
        )
        return agent

    # ------------------------------------------------------------------
    # 3. Session
    # ------------------------------------------------------------------
    def start_session(self, task_id: str, agent_id: str, session_id: Optional[str] = None) -> Session:
        self._require_task(task_id)
        self._require_agent(agent_id)
        session = Session(
            session_id=session_id or f"{task_id}-session-{_short_id()}",
            task_id=task_id,
            agent_id=agent_id,
            status=SessionStatus.ACTIVE,
        )
        self._sessions.create(session)
        self._emit(
            "session.started",
            task_id=task_id,
            session_id=session.session_id,
            agent_id=agent_id,
        )
        return session

    # ------------------------------------------------------------------
    # 4-8. Turn: context -> model request -> model response -> tool
    #      request(s) -> observation(s)
    # ------------------------------------------------------------------
    def run_turn(self, session_id: str, extra_context: Optional[dict[str, Any]] = None) -> Turn:
        session = self._require_session(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise IllegalRuntimeTransition(
                f"Cannot run a turn on session {session_id} in status {session.status.value}"
            )
        task = self._require_task(session.task_id)

        next_sequence = len(self._turns.list_for_session(session_id)) + 1
        turn = Turn(
            turn_id=f"{session_id}-turn-{next_sequence}",
            session_id=session_id,
            sequence_number=next_sequence,
            status=TurnStatus.STARTED,
        )
        self._turns.create(turn)
        self._emit(
            "turn.started",
            task_id=task.task_id,
            session_id=session_id,
            agent_id=session.agent_id,
            payload={"sequence_number": next_sequence},
        )

        # -- Context acquisition (deliberately minimal; see context.py) --
        recent_events = self._events.list_for_task(task.task_id)[-10:]
        context = assemble_context(task, session, recent_events)
        if extra_context:
            context = {**context, **extra_context}

        # -- Model request/response --
        turn.status = TurnStatus.AWAITING_MODEL
        turn.model_request = context
        self._turns.update(turn)

        response = self._gateway.send(context)
        turn.model_response = response
        self._emit(
            "model.response_received",
            task_id=task.task_id,
            session_id=session_id,
            agent_id=session.agent_id,
            payload={"turn_id": turn.turn_id},
        )

        # -- Tool request(s) / observation(s) --
        tool_calls = response.get("tool_calls") or []
        rounds = 0
        recorded_tool_calls: list[dict[str, Any]] = []
        while tool_calls and rounds < _MAX_TOOL_ROUNDS_PER_TURN:
            rounds += 1
            for call in tool_calls:
                turn.status = TurnStatus.AWAITING_TOOL
                self._turns.update(turn)
                self._emit(
                    "tool.requested",
                    task_id=task.task_id,
                    session_id=session_id,
                    agent_id=session.agent_id,
                    payload={"turn_id": turn.turn_id, "tool_call": call},
                )

                observation = self._tools.execute(call)
                recorded_tool_calls.append({"request": call, "observation": observation})
                self._emit(
                    "tool.observation_received",
                    task_id=task.task_id,
                    session_id=session_id,
                    agent_id=session.agent_id,
                    payload={"turn_id": turn.turn_id, "observation": observation},
                )
            # A real Gateway/loop policy may choose to send observations
            # back to the model for a follow-up response; Core does not
            # decide that policy here (out of scope), so tool_calls does
            # not auto-repeat unless the fake/gateway explicitly says so
            # via a fresh response. This stage assumes at most one round
            # unless a test double is specifically written to loop.
            tool_calls = []

        turn.tool_calls = recorded_tool_calls
        turn.status = TurnStatus.COMPLETED
        self._turns.update(turn)
        self._emit(
            "turn.completed",
            task_id=task.task_id,
            session_id=session_id,
            agent_id=session.agent_id,
            payload={"turn_id": turn.turn_id, "sequence_number": next_sequence},
        )
        return turn

    # ------------------------------------------------------------------
    # 11. Checkpoint
    # ------------------------------------------------------------------
    def checkpoint(self, task_id: str, session_id: str, agent_id: str, label: Optional[str] = None) -> Checkpoint:
        task = self._require_task(task_id)
        turns = self._turns.list_for_session(session_id)
        last_turn = turns[-1] if turns else None

        cp = Checkpoint(
            checkpoint_id=f"{task_id}-checkpoint-{_short_id()}",
            task_id=task_id,
            session_id=session_id,
            agent_id=agent_id,
            label=label,
            state={
                "task_status": task.status.value,
                "last_turn_id": last_turn.turn_id if last_turn else None,
                "last_sequence_number": last_turn.sequence_number if last_turn else 0,
            },
        )
        self._checkpoints.create(cp)
        self._emit(
            "checkpoint.created",
            task_id=task_id,
            session_id=session_id,
            agent_id=agent_id,
            payload={"checkpoint_id": cp.checkpoint_id},
        )
        return cp

    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------
    def complete_task(self, task_id: str) -> Task:
        task = self._require_task(task_id)
        if task.status == TaskStatus.EXECUTING:
            task.transition_to(TaskStatus.VERIFYING)
        task.transition_to(TaskStatus.COMPLETED)
        self._tasks.update(task)
        self._emit("task.completed", task_id=task_id)
        return task

    # ------------------------------------------------------------------
    # 13-14. Recover: reconstruct enough state for a NEW runtime instance
    # (a new process, per the recovery test) to continue or complete.
    # ------------------------------------------------------------------
    def resume(self, task_id: str) -> "RuntimeState":
        task = self._require_task(task_id)
        agents = self._agents.list_for_task(task_id)
        sessions = self._sessions.list_for_task(task_id)
        latest_checkpoint = self._checkpoints.latest_for_task(task_id)

        active_session = next((s for s in sessions if s.status == SessionStatus.ACTIVE), None)
        turns = self._turns.list_for_session(active_session.session_id) if active_session else []

        self._emit(
            "task.resumed",
            task_id=task_id,
            payload={"checkpoint_id": latest_checkpoint.checkpoint_id if latest_checkpoint else None},
        )
        return RuntimeState(
            task=task,
            agents=agents,
            active_session=active_session,
            turns=turns,
            latest_checkpoint=latest_checkpoint,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _require_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise IllegalRuntimeTransition(f"Task not found: {task_id}")
        return task

    def _require_agent(self, agent_id: str) -> Agent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise IllegalRuntimeTransition(f"Agent not found: {agent_id}")
        return agent

    def _require_session(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise IllegalRuntimeTransition(f"Session not found: {session_id}")
        return session

    def _emit(
        self,
        event_type: str,
        task_id: str,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        self._events.append(
            Event(
                event_id=f"evt-{uuid.uuid4().hex}",
                event_type=event_type,
                task_id=task_id,
                session_id=session_id,
                agent_id=agent_id,
                actor="core-runtime",
                payload=payload or {},
                timestamp=datetime.now(timezone.utc),
            )
        )


class RuntimeState:
    """Snapshot returned by AgentRuntime.resume(). Plain data holder -- not
    persisted itself; it's a read model assembled from repositories so a
    caller (the future agent loop driver, or a test) knows where execution
    left off."""

    def __init__(
        self,
        task: Task,
        agents: list[Agent],
        active_session: Optional[Session],
        turns: list[Turn],
        latest_checkpoint: Optional[Checkpoint],
    ) -> None:
        self.task = task
        self.agents = agents
        self.active_session = active_session
        self.turns = turns
        self.latest_checkpoint = latest_checkpoint


def _short_id() -> str:
    return uuid.uuid4().hex[:8]
