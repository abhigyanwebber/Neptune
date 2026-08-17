"""Runtime Driver Layer (A-005).

AgentRuntime (engine.py) provides the durable primitives -- create_task,
start_agent_run, start_session, run_turn, checkpoint, resume,
complete_task -- but deliberately does not decide *when* to call them
repeatedly (ADR-A-006: "sending observations back for a follow-up model
response is loop policy ... belongs to a future driver, not to Core's
control-plane primitives"). RuntimeDriver is that future driver.

RuntimeDriver uses AgentRuntime exclusively through its public methods --
it never reaches into AgentRuntime's private repository attributes. This
keeps the driver replaceable (a smarter policy is a new class implementing
the same shape) without the engine needing to change.

Policy implemented here is deliberately the simplest one that satisfies
the lifecycle: run a turn, look at whether the model asked for tools, and
either continue, complete, or stop. See 05_DECISIONS/ADR-038 for the full
rationale and what a future, smarter policy might change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from core.domain.checkpoint import Checkpoint
from core.domain.task import Task
from core.domain.turn import Turn

from .engine import AgentRuntime

# Ceiling on turns per execute_task()/execute_until_stop() call. Distinct
# from engine.py's _MAX_TOOL_ROUNDS_PER_TURN, which bounds tool-call rounds
# *within* a single turn and is owned entirely by AgentRuntime.run_turn --
# the driver never touches that constant, it only respects that a turn
# will eventually return regardless of what the model does inside it.
DEFAULT_MAX_TURNS = 25


class DriverOutcome(str, Enum):
    COMPLETED = "completed"
    STOPPED_MAX_TURNS = "stopped_max_turns"
    STOPPED_TOOL_FAILURE = "stopped_tool_failure"
    STOPPED_NO_ACTIVE_SESSION = "stopped_no_active_session"


@dataclass
class DriverConfig:
    max_turns: int = DEFAULT_MAX_TURNS
    checkpoint_every: int = 1  # checkpoint after every N turns; 0 disables periodic checkpoints
    default_role: str = "core-implementer"


@dataclass
class DriverResult:
    outcome: DriverOutcome
    task_id: str
    turns_run: list[Turn] = field(default_factory=list)
    last_checkpoint: Optional[Checkpoint] = None
    task: Optional[Task] = None  # populated only on COMPLETED (from complete_task's return)


class RuntimeDriver:
    def __init__(self, runtime: AgentRuntime, config: Optional[DriverConfig] = None) -> None:
        self._runtime = runtime
        self._config = config or DriverConfig()

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    def execute_task(
        self,
        task_id: str,
        role: Optional[str] = None,
        requirements: Optional[list[str]] = None,
        constraints: Optional[dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> DriverResult:
        """Fresh execution: create the task, start an agent run and
        session, then drive turns until stop. Use execute_until_stop()
        instead for a task that already exists (e.g. after a restart)."""
        self._runtime.create_task(
            task_id, requirements=requirements, constraints=constraints, project_id=project_id
        )
        agent = self._runtime.start_agent_run(task_id, role=role or self._config.default_role)
        session = self._runtime.start_session(task_id, agent.agent_id)
        return self._run_loop(task_id, session.session_id, agent.agent_id, turns_already_run=0)

    def execute_until_stop(self, task_id: str) -> DriverResult:
        """Resume-and-drive: reconstructs execution state via
        AgentRuntime.resume() and runs turns until should_complete(), a
        tool failure, or max_turns is reached.

        This is also the recovery path: calling this after a process
        restart continues exactly where the last checkpoint left off,
        because AgentRuntime.resume() reconstructs state purely from
        Postgres (see tests/integration/runtime/test_driver_recovery.py).
        """
        state = self._runtime.resume(task_id)
        if state.active_session is None:
            return DriverResult(outcome=DriverOutcome.STOPPED_NO_ACTIVE_SESSION, task_id=task_id)

        return self._run_loop(
            task_id, state.active_session.session_id, state.active_session.agent_id, len(state.turns)
        )

    # ------------------------------------------------------------------
    # Policy (see ADR-038 -- deliberately simple, deliberately replaceable)
    # ------------------------------------------------------------------
    @staticmethod
    def tool_failed(turn: Turn) -> bool:
        """A tool call's observation is considered failed if it explicitly
        reports status == "error". Anything else (including tool ports
        that don't set a status field at all) is treated as not-failed --
        the driver has no opinion on tool-specific error shapes beyond
        this one convention, which fakes.FakeToolPort already follows."""
        return any(
            (call.get("observation") or {}).get("status") == "error" for call in turn.tool_calls
        )

    @staticmethod
    def should_complete(turn: Turn) -> bool:
        """The model's response is treated as final when it made no tool
        calls this turn -- the simplest possible signal, matching the
        director's brief step 4 ("If model returns final response:
        complete task")."""
        return len(turn.tool_calls) == 0

    @classmethod
    def should_continue(cls, turn: Turn) -> bool:
        """Continue driving turns only when the model asked for tools and
        none of them failed. This is the complement of should_complete()
        and tool_failed() -- kept as a separate method (rather than
        inlining `not should_complete and not tool_failed`) because a
        future policy may want continue/complete/fail to diverge instead
        of being strict complements of each other."""
        return len(turn.tool_calls) > 0 and not cls.tool_failed(turn)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _run_loop(self, task_id: str, session_id: str, agent_id: str, turns_already_run: int) -> DriverResult:
        turns_run: list[Turn] = []
        last_checkpoint: Optional[Checkpoint] = None
        turn_index = turns_already_run

        while turn_index < self._config.max_turns:
            turn = self._runtime.run_turn(session_id)
            turns_run.append(turn)
            turn_index += 1

            if self._config.checkpoint_every and turn_index % self._config.checkpoint_every == 0:
                last_checkpoint = self._runtime.checkpoint(
                    task_id, session_id, agent_id, label=f"turn-{turn_index}"
                )

            if self.tool_failed(turn):
                return DriverResult(
                    outcome=DriverOutcome.STOPPED_TOOL_FAILURE,
                    task_id=task_id,
                    turns_run=turns_run,
                    last_checkpoint=last_checkpoint,
                )

            if self.should_complete(turn):
                task = self._runtime.complete_task(task_id)
                if last_checkpoint is None:
                    last_checkpoint = self._runtime.checkpoint(
                        task_id, session_id, agent_id, label="final"
                    )
                return DriverResult(
                    outcome=DriverOutcome.COMPLETED,
                    task_id=task_id,
                    turns_run=turns_run,
                    last_checkpoint=last_checkpoint,
                    task=task,
                )

            if not self.should_continue(turn):
                # Not complete, not a tool failure, and policy says don't
                # continue either -- shouldn't happen given should_complete
                # and should_continue are complements above, but a future
                # policy might make this reachable, so it's handled rather
                # than assumed impossible.
                break

        return DriverResult(
            outcome=DriverOutcome.STOPPED_MAX_TURNS,
            task_id=task_id,
            turns_run=turns_run,
            last_checkpoint=last_checkpoint,
        )
