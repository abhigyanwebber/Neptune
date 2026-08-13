"""Shared fixtures for Gateway Foundation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from neptune.infrastructure.models.registry import ModelRegistry
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "registries"


@pytest.fixture
def model_registry() -> ModelRegistry:
    return ModelRegistry.load(CONFIG_DIR)


@pytest.fixture
def capability_router() -> CapabilityRouter:
    return CapabilityRouter()


@pytest.fixture
def mock_adapter() -> MockProviderAdapter:
    return MockProviderAdapter()
