"""Gate 3: provider independence of core.

Static check that src/core (domain + contracts) never imports SQLAlchemy,
psycopg2, or anything under infrastructure/. This is the enforceable form
of Bible 02_ARCHITECTURE/02_DEPENDENCY_DIRECTION.md: projects/core must not
depend on providers or infrastructure.

This check exists from Stage 0 even though there are no provider SDKs yet,
per the director's instruction that it "should exist from the start."
"""
import ast
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[2] / "src" / "core"

FORBIDDEN_MODULE_PREFIXES = (
    "sqlalchemy",
    "psycopg2",
    "asyncpg",
    "infrastructure",
    "application",
    "interfaces",
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


def test_core_has_no_infrastructure_or_provider_imports():
    violations: list[str] = []
    for py_file in CORE_DIR.rglob("*.py"):
        source = py_file.read_text()
        for module in _imported_modules(source):
            if module.startswith(FORBIDDEN_MODULE_PREFIXES):
                violations.append(f"{py_file.relative_to(CORE_DIR.parents[1])}: imports '{module}'")
    assert not violations, "core/ must stay provider/infrastructure independent:\n" + "\n".join(
        violations
    )
