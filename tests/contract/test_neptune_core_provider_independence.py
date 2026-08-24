"""Provider-independence check for neptune.core (C-005 item 4).

Mirrors tests/contract/test_core_provider_independence.py's exact
methodology (static AST import scan, no runtime/registry dependency)
applied to Claude B's core tree instead of Claude A's. Per
DIRECTOR_REVIEW_001.md risk #7: "there is no automated test enforcing
this for B's tree -- the existing test only scans src/core."

This is a pure static analysis test: it parses source files and
inspects import statements. It reads no registry data, touches no
database, and does not depend on any registry-consolidation work
(C-004 or otherwise) -- it can be added independently, per C-005 item
4's instruction to add the narrow test only if it is genuinely
independent of unfinished C-004 work. It is.

Note: neptune.core.contracts.provider_adapter.py deliberately imports
neptune.core.contracts.model_gateway (a sibling core module, not
infrastructure) to reuse shared types (ContextMessage, ModelUsage,
etc.) -- this is intra-core sharing, not a provider/infrastructure
leak, and is correctly allowed by this check (only prefixes rooted at
infrastructure/application/provider-SDK names are forbidden, not all
imports).
"""
import ast
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[2] / "src" / "neptune" / "core"

FORBIDDEN_MODULE_PREFIXES = (
    # Provider SDKs / HTTP clients (confirmed used by neptune's own
    # provider adapters -- must never appear inside core).
    "requests",
    "litellm",
    "groq",
    "openai",
    "anthropic",
    "google",
    # Persistence (confirmed used by Claude A's infrastructure layer;
    # core owning no persistence of its own is ADR-009's principle).
    "sqlalchemy",
    "psycopg2",
    "asyncpg",
    # Same-lane infrastructure/application layering.
    "neptune.infrastructure",
    "neptune.application",
    "infrastructure",
    "application",
    "interfaces",
    # Cross-lane: core must not depend on Claude A's tree either.
    "core",
)


def _imported_modules(source: str) -> list[str]:
    tree = ast.parse(source)
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_neptune_core_has_no_infrastructure_or_provider_imports():
    violations: list[str] = []
    for py_file in CORE_DIR.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for module in _imported_modules(source):
            if module.startswith(FORBIDDEN_MODULE_PREFIXES):
                violations.append(
                    f"{py_file.relative_to(CORE_DIR.parents[2])}: imports '{module}'"
                )
    assert not violations, (
        "neptune/core/ must stay provider/infrastructure independent:\n"
        + "\n".join(violations)
    )
