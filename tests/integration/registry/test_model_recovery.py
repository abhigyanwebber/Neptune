"""Model persistence + process-death recovery (C-004): genuine two-OS-process
test against live Postgres, matching the pattern already established for
the other four registries (A-003/A-004) -- register a Model (and its
Provider) in one process, kill it, then a second unrelated process reads
the model back, confirms verification metadata survived, and resolves its
dependency on its provider through the same generic mechanism used
elsewhere in the registry system.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url

SCRIPT = Path(__file__).parent / "_model_recovery_script.py"


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


def test_model_survives_process_termination_and_restart():
    write_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "write"], capture_output=True, text=True, timeout=30
    )
    assert write_proc.returncode == 0, write_proc.stderr

    read_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "read"], capture_output=True, text=True, timeout=30
    )
    assert read_proc.returncode == 0, read_proc.stderr
    result = json.loads(read_proc.stdout.strip().splitlines()[-1])

    assert result["model_found"] is True
    assert result["provider_id"] == "groq"
    assert result["provider_model_name"] == "llama-3.3-70b-versatile"
    assert set(result["capabilities"]) == {"coding", "tool_use"}
    assert result["status"] == "available"
    assert result["verification_status"] == "verified"
    assert result["verification_source"] == "B-003 live validation"
    assert result["provider_found"] is True
    assert result["provider_endpoints"] == ["https://api.groq.com/openai/v1"]
    assert result["dependency_resolution_order"] == ["groq", "groq-llama-3.3-70b-versatile"]
