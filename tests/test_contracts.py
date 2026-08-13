"""Contract-compliance tests.

Verifies: (1) required MODEL_CONTRACT/PROVIDER_CONTRACT/ROUTER_CONTRACT
shapes exist and validate; (2) MockProviderAdapter and GroqAdapter
structurally satisfy the ProviderAdapter Protocol; (3) core modules
never import a provider SDK (PROVIDER_CONTRACT invariant 3 / ADR-024),
checked statically so it cannot silently regress.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from neptune.core.contracts.model_gateway import ModelRequest
from neptune.core.contracts.provider_adapter import ProviderAdapter
from neptune.core.contracts.router import Router
from neptune.core.domain import Capability
from neptune.infrastructure.providers.groq_adapter import GroqAdapter
from neptune.infrastructure.providers.reference_adapter import MockProviderAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter

CORE_DIR = Path(__file__).resolve().parent.parent / "src" / "neptune" / "core"

FORBIDDEN_IMPORT_ROOTS = {"litellm", "groq", "openai", "anthropic", "google"}


def test_model_request_requires_capabilities() -> None:
    with pytest.raises(Exception):
        ModelRequest(task_id="t1", session_id="s1", turn_id="tu1", capabilities=[])


def test_model_request_minimal_valid() -> None:
    req = ModelRequest(
        task_id="t1",
        session_id="s1",
        turn_id="tu1",
        capabilities=[Capability.FAST_GENERAL],
    )
    assert req.correlation_id
    assert req.capabilities == [Capability.FAST_GENERAL]


def test_mock_adapter_satisfies_provider_adapter_protocol() -> None:
    adapter = MockProviderAdapter()
    assert isinstance(adapter, ProviderAdapter)


def test_groq_adapter_satisfies_provider_adapter_protocol() -> None:
    adapter = GroqAdapter()
    assert isinstance(adapter, ProviderAdapter)


def test_capability_router_satisfies_router_protocol() -> None:
    router = CapabilityRouter()
    assert isinstance(router, Router)


def _imported_roots(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_core_never_imports_provider_sdks() -> None:
    """Static enforcement of PROVIDER_CONTRACT invariant 3 and
    ADR-024: no provider SDK or model-vendor name may appear as an
    import inside neptune.core.*."""
    offenders: dict[str, set[str]] = {}
    for py_file in CORE_DIR.rglob("*.py"):
        roots = _imported_roots(py_file) & FORBIDDEN_IMPORT_ROOTS
        if roots:
            offenders[str(py_file)] = roots
    assert not offenders, f"provider SDK imports leaked into core: {offenders}"


def test_infrastructure_may_import_provider_sdks() -> None:
    """Sanity check that the guard above is actually meaningful, i.e.
    it isn't just that nothing in the repo imports litellm at all."""
    groq_adapter_path = (
        Path(__file__).resolve().parent.parent
        / "src" / "neptune" / "infrastructure" / "providers" / "groq_adapter.py"
    )
    source = groq_adapter_path.read_text()
    assert "import litellm" in source
