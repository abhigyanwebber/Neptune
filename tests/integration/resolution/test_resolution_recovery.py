"""Resolution recovery (A-006 integration requirement): load registry
seed, perform resolution, recover the SAME result after restart.

Two genuinely separate OS processes against live Postgres: process A
loads the real verified seed data (06_REGISTRIES/data/*.yaml) and resolves
a provider for "reasoning", then exits. Process B reconnects (registries
already populated -- it does not reload) and performs the identical
resolution, proving the result is reproducible from durable registry
state alone, with no reliance on anything held in process A's memory.
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

SCRIPT = Path(__file__).parent / "_resolution_recovery_script.py"


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


def test_resolution_result_is_reproducible_across_process_restart():
    load_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "load_and_resolve"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert load_proc.returncode == 0, load_proc.stderr
    first_result = json.loads(load_proc.stdout.strip().splitlines()[-1])
    assert first_result["load_errors"] == []
    assert first_result["provider_id"] is not None

    resolve_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "resolve_only"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert resolve_proc.returncode == 0, resolve_proc.stderr
    second_result = json.loads(resolve_proc.stdout.strip().splitlines()[-1])

    # Same capability, same selected provider, same dependency chain, same
    # eligible-candidate set, same selection reasoning -- everything the
    # first process computed is exactly reproduced by the second, purely
    # from what's durable in Postgres.
    assert second_result["capability"] == first_result["capability"]
    assert second_result["provider_id"] == first_result["provider_id"]
    assert second_result["dependencies"] == first_result["dependencies"]
    assert second_result["eligible_provider_ids"] == first_result["eligible_provider_ids"]
    assert second_result["selection_reason"] == first_result["selection_reason"]
