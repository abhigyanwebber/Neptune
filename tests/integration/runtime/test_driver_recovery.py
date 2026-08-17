"""Driver-level checkpoint + resume across a genuine process boundary
(A-005 integration requirement: "checkpoint + resume during execution"
and "full multi-turn runtime cycle").

Two separate OS processes against live Postgres: process A drives a task
partway (stopped by max_turns, having checkpointed after each turn), then
exits. Process B resumes via RuntimeDriver.execute_until_stop() and
completes the task -- proving the driver's stop/resume boundary survives
a real process death, not just a fresh in-memory call.
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

SCRIPT = Path(__file__).parent / "_driver_recovery_script.py"


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


def test_driver_checkpoint_and_resume_across_process_restart():
    task_id = f"driver-recovery-{uuid.uuid4().hex[:8]}"

    # Phase 1: partial execution, stopped by max_turns, exits.
    partial_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "run_partial", task_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert partial_proc.returncode == 0, partial_proc.stderr
    partial_result = json.loads(partial_proc.stdout.strip().splitlines()[-1])

    assert partial_result["outcome"] == "stopped_max_turns"
    assert partial_result["turns_run"] == 2
    assert partial_result["checkpoint_id"] is not None

    # Phase 2: a new, unrelated process resumes and finishes.
    resume_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "resume_and_finish", task_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert resume_proc.returncode == 0, resume_proc.stderr
    resume_result = json.loads(resume_proc.stdout.strip().splitlines()[-1])

    assert resume_result["outcome"] == "completed"
    assert resume_result["turns_run_this_call"] == 1  # only the one new turn after resuming
    assert resume_result["final_task_status"] == "completed"
    assert resume_result["checkpoint_id"] is not None
