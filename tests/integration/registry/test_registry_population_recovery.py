"""Registry population + audit + snapshot, proven across a real process
death (A-004): load the verified seed data in one OS process, kill it,
then a second unrelated process verifies the catalog, the audit trail,
and a snapshot export -- all from Postgres alone.
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

SCRIPT = Path(__file__).parent / "_registry_population_script.py"


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


def test_population_survives_process_termination_and_is_auditable():
    load_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "load"], capture_output=True, text=True, timeout=30
    )
    assert load_proc.returncode == 0, load_proc.stderr
    load_result = json.loads(load_proc.stdout.strip().splitlines()[-1])
    assert load_result["errors"] == []
    assert load_result["providers_loaded"] == 5
    assert load_result["capabilities_loaded"] == 10
    assert load_result["resources_loaded"] == 6
    assert load_result["tools_loaded"] == 5

    verify_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "verify"], capture_output=True, text=True, timeout=30
    )
    assert verify_proc.returncode == 0, verify_proc.stderr
    result = json.loads(verify_proc.stdout.strip().splitlines()[-1])

    assert result["groq_found"] is True
    assert result["groq_verification_status"] == "verified"
    assert result["ollama_found"] is True
    assert result["openai_compatible_found"] is True
    assert result["audit_events_present"] is True
    assert result["audit_event_types_include_provider_registered"] is True
    assert result["snapshot_provider_count"] == result["provider_count"]
    assert result["snapshot_schema_version"] == "1.0"
