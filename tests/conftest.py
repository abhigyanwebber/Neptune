"""Shared fixtures for both Claude B (Gateway Foundation, tool
execution, observation loop) and Claude A (Core Runtime schema) test
suites, combined here after merging worker/claude-a into
worker/claude-b for B-006's cross-branch recovery validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neptune.infrastructure.models.registry import ModelRegistry
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "registries"
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = REPO_ROOT / "09_SCHEMAS"


@pytest.fixture
def model_registry() -> ModelRegistry:
    return ModelRegistry.load(CONFIG_DIR)


@pytest.fixture
def capability_router() -> CapabilityRouter:
    return CapabilityRouter()


@pytest.fixture
def mock_adapter() -> MockProviderAdapter:
    return MockProviderAdapter()


@pytest.fixture(scope="session")
def task_schema() -> dict:
    return json.loads((SCHEMAS_DIR / "task.schema.json").read_text())


@pytest.fixture(scope="session")
def event_schema() -> dict:
    return json.loads((SCHEMAS_DIR / "event.schema.json").read_text())
