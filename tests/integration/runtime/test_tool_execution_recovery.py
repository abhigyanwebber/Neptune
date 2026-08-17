"""Tool Execution Recovery Validation (B-006).

Extends A-005's driver-level recovery test
(tests/integration/runtime/test_driver_recovery.py) with REAL tool
execution: process A runs a turn that calls Neptune's real EchoTool
(via ToolPortAdapter -> ToolExecutorService, B-004), then exits.
Process B resumes via RuntimeDriver.execute_until_stop() and
completes the task -- proving tool-execution state (the observation)
survives a genuine process boundary using persisted state only, and
that the tool is not re-executed on resume.

Required proof, mapped to assertions below:
    Task -> Tool Call -> Tool Executes -> Observation Recorded ->
    Runtime Stops -> Fresh Process Starts -> Resume -> Continue
    Execution -> Final Answer
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url

SCRIPT = Path(__file__).parent / "_tool_execution_recovery_script.py"


def _postgres_available() -> bool:
    try:
        engine = create_engine(get_database_url(), future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


def _run_script(mode: str, task_id: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), mode, task_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _event_counts(task_id: str) -> dict[str, int]:
    engine = create_engine(get_database_url(), future=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT event_type, count(*) FROM events "
                "WHERE task_id = :task_id "
                "AND event_type IN ('tool.requested', 'tool.observation_received') "
                "GROUP BY event_type"
            ),
            {"task_id": task_id},
        )
        return {row[0]: row[1] for row in rows}


def test_tool_execution_survives_process_restart_and_is_not_repeated():
    task_id = f"tool-exec-recovery-{uuid.uuid4().hex[:8]}"

    # --- Phase 1: real tool executes, process exits (simulated crash) ---
    partial = _run_script("run_partial", task_id)

    # 1. Tool execution occurred before interruption.
    assert partial["outcome"] == "stopped_max_turns"
    assert partial["turns_run"] == 1
    tool_calls = partial["last_turn_tool_calls"]
    assert len(tool_calls) == 1
    observation = tool_calls[0]["observation"]
    assert observation["status"] == "ok"
    assert observation["outcome"] == "success"
    assert observation["result"] == {"echo": "hello"}  # the REAL EchoTool's output

    # 2. Observation is persisted (checked independently of the
    #    script's own stdout, via a separate DB connection, proving
    #    it's actually durable and not just returned in-process).
    assert partial["checkpoint_id"] is not None
    counts_after_phase_1 = _event_counts(task_id)
    assert counts_after_phase_1.get("tool.requested") == 1
    assert counts_after_phase_1.get("tool.observation_received") == 1

    # --- Phase 2: brand-new process resumes and finishes ---
    resumed = _run_script("resume_and_finish", task_id)

    # 3 & 4. Fresh process loaded task state and continued correctly.
    assert resumed["outcome"] == "completed"
    assert resumed["turns_run_this_call"] == 1  # only the one new turn
    assert resumed["final_task_status"] == "completed"

    # 5. Tool is NOT executed twice: event counts unchanged after
    #    resume -- the second turn's gateway response had no
    #    tool_calls, so ToolPortAdapter.execute() was never called
    #    again in the resumed process.
    counts_after_phase_2 = _event_counts(task_id)
    assert counts_after_phase_2.get("tool.requested") == 1
    assert counts_after_phase_2.get("tool.observation_received") == 1

    # 6. Final answer completes successfully.
    assert resumed["final_model_response"]["content"] == "Done -- echo returned hello"
    assert resumed["final_model_response"]["tool_calls"] == []
