"""Registry persistence + process-death recovery.

Two genuinely separate OS processes against live Postgres: one registers
a small provider/resource/tool/capability graph and exits, a second
unrelated process reconnects, reads the catalog back, performs a
capability lookup, and resolves a dependency chain -- all purely from
Postgres, same pattern as tests/integration/persistence/test_recovery.py
and tests/integration/runtime/test_runtime_recovery.py.
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

SCRIPT = Path(__file__).parent / "_registry_recovery_script.py"


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


def test_registry_survives_process_termination_and_restart():
    write_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "write"], capture_output=True, text=True, timeout=30
    )
    assert write_proc.returncode == 0, write_proc.stderr

    read_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "read"], capture_output=True, text=True, timeout=30
    )
    assert read_proc.returncode == 0, read_proc.stderr
    result = json.loads(read_proc.stdout.strip().splitlines()[-1])

    assert result["capability_count"] >= 2
    assert result["browser_tool_found"] is True
    assert result["browser_tool_depends_on"] == ["docker"]
    assert result["groq_provider_found"] is True
    assert set(result["groq_capabilities"]) == {"coding", "reasoning"}
    assert "groq" in result["coding_providers"]
    assert result["resource_count"] >= 2
    assert result["dependency_resolution_order"] == ["docker", "browser"]
