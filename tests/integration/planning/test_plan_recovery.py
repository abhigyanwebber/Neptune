"""A-007 integration requirement, demonstrated literally:

    Plan -> Execute Step 1 -> Persist -> Reload -> Execute Step 2 -> Complete

using existing persistence infrastructure. Two genuinely separate OS
processes against live Postgres -- same pattern as every other recovery
test in this codebase (persistence, registry, resolution, runtime,
driver).
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

SCRIPT = Path(__file__).parent / "_plan_recovery_script.py"


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


def test_plan_executes_step1_persists_reloads_executes_step2_completes():
    plan_id = f"plan-recovery-{uuid.uuid4().hex[:8]}"

    # Phase 1: create plan, execute step 1, persist, exit (process dies).
    step1_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "step1", plan_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert step1_proc.returncode == 0, step1_proc.stderr
    step1_result = json.loads(step1_proc.stdout.strip().splitlines()[-1])

    assert step1_result["step1_status"] == "completed"
    assert step1_result["step2_status"] == "pending"
    assert step1_result["is_complete"] is False

    # Phase 2: a new, unrelated process reloads the plan and finishes it.
    step2_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "step2_and_complete", plan_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert step2_proc.returncode == 0, step2_proc.stderr
    step2_result = json.loads(step2_proc.stdout.strip().splitlines()[-1])

    assert step2_result["step1_status"] == "completed"
    assert step2_result["step2_status"] == "completed"
    assert step2_result["is_complete"] is True
    assert step2_result["all_succeeded"] is True
