import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = REPO_ROOT / "09_SCHEMAS"


@pytest.fixture(scope="session")
def task_schema() -> dict:
    return json.loads((SCHEMAS_DIR / "task.schema.json").read_text())


@pytest.fixture(scope="session")
def event_schema() -> dict:
    return json.loads((SCHEMAS_DIR / "event.schema.json").read_text())
