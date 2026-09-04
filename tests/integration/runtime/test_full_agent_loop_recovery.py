"""Full agent loop -- persistence/recovery composition (B-009 Phase 4).

Extends B-006's tool-execution recovery proof to the FULL loop: the
tool call, its real observation, a genuine process restart, and a
second real Turn that completes using the persisted observation --
all using existing checkpoint/persistence mechanisms, no redesign.
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

SCRIPT = Path(__file__).parent / "_full_agent_loop_recovery_script.py"


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


def test_full_loop_survives_process_restart_with_real_tool_and_observation() -> None:
    task_id = f"full-loop-recovery-{uuid.uuid4().hex[:8]}"

    # --- Phase 1: turn 1 -- model decides to call echo, real tool
    #     executes, real observation persisted, process exits ---
    partial = _run_script("run_partial", task_id)

    assert partial["outcome"] == "stopped_max_turns"
    assert partial["turns_run"] == 1
    tool_calls = partial["last_turn_tool_calls"]
    assert len(tool_calls) == 1
    observation = tool_calls[0]["observation"]
    assert observation["status"] == "ok"
    assert observation["outcome"] == "success"
    assert observation["result"] == {"echo": "NEPTUNE_FULL_LOOP_OK"}  # the REAL EchoTool's output
    assert partial["checkpoint_id"] is not None

    # --- Phase 2: brand-new process resumes ---
    resumed = _run_script("resume_and_finish", task_id)

    # Fresh process's model request genuinely carried the persisted
    # observation forward -- this is the actual recovery+continuation
    # proof, not just "the process didn't crash."
    assert "tool.observation_received" in resumed["gateway_saw_recent_events"]

    assert resumed["outcome"] == "completed"
    assert resumed["turns_run_this_call"] == 1  # only the new turn -- no re-execution
    assert resumed["final_task_status"] == "completed"
    assert resumed["final_model_response"]["content"] == "NEPTUNE_FULL_LOOP_DONE"
    assert resumed["final_model_response"]["tool_calls"] == []
