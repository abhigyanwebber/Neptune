"""Success criteria 12-15 from the director's brief:

    12. Terminate the runtime.
    13. Restart.
    14. Resume the execution state.
    15. Continue or complete the task without losing durable state.

Two genuinely separate OS subprocesses against live Postgres, exactly like
tests/integration/persistence/test_recovery.py but exercising the full
AgentRuntime (create -> agent run -> session -> turn -> checkpoint -> kill
-> new process -> resume -> one more turn -> complete).
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

SCRIPT = Path(__file__).parent / "_runtime_recovery_script.py"


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


def test_runtime_survives_process_termination_and_resumes():
    task_id = f"runtime-recovery-{uuid.uuid4().hex[:8]}"

    # Phase 1: process runs task through turn 1 + checkpoint, then exits.
    write_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "write", task_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert write_proc.returncode == 0, write_proc.stderr
    write_result = json.loads(write_proc.stdout.strip().splitlines()[-1])
    assert write_result["checkpoint_id"]

    # Phase 2: a new, unrelated process constructs a fresh AgentRuntime,
    # resumes purely from Postgres, drives one more turn, and completes
    # the task.
    resume_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "resume", task_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert resume_proc.returncode == 0, resume_proc.stderr
    result = json.loads(resume_proc.stdout.strip().splitlines()[-1])

    assert result["recovered_task_status_before_resume"] == "executing"
    assert result["recovered_turn_count"] == 1
    assert result["recovered_latest_checkpoint_id"] == write_result["checkpoint_id"]
    assert result["next_turn_sequence_number"] == 2
    assert result["final_task_status"] == "completed"
