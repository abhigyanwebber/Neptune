"""Gate 2 (part 2) + the director's explicit recovery test:

create task -> create session -> record turn/event -> checkpoint ->
terminate process -> restart -> recover state.

Requires a live Postgres reachable at NEPTUNE_DATABASE_URL (see
docker-compose.yml at repo root: `docker compose up -d`). Skips cleanly if
unreachable, rather than failing Stage 0/1 CI on missing infra.
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

SCRIPT = Path(__file__).parent / "_recovery_script.py"


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


def test_state_survives_process_termination_and_restart():
    task_id = f"recovery-{uuid.uuid4().hex[:8]}"

    # Phase 1: a process writes state, then genuinely exits.
    write_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "write", task_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert write_proc.returncode == 0, write_proc.stderr
    write_result = json.loads(write_proc.stdout.strip().splitlines()[-1])
    assert write_result["checkpoint_id"] == f"{task_id}-checkpoint-1"

    # Phase 2: a brand-new, unrelated OS process reconnects and reads.
    # It shares no memory, no Python objects, no ORM identity map with
    # phase 1 -- only the Postgres database on disk.
    read_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "read", task_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert read_proc.returncode == 0, read_proc.stderr
    recovered = json.loads(read_proc.stdout.strip().splitlines()[-1])

    assert recovered["task"] is not None
    assert recovered["task"]["task_id"] == task_id
    assert recovered["task"]["status"] == "executing"

    assert recovered["agent"] is not None
    assert recovered["agent"]["role"] == "core-implementer"

    assert recovered["session"] is not None
    assert recovered["session"]["task_id"] == task_id

    assert recovered["turn_count"] == 1
    assert recovered["event_count"] == 1

    assert recovered["latest_checkpoint"] is not None
    assert recovered["latest_checkpoint"]["checkpoint_id"] == f"{task_id}-checkpoint-1"
    assert recovered["latest_checkpoint"]["state"]["task_status"] == "executing"
