"""Integration test (B-010): canonical registry -> ToolDefinition ->
ToolPort -> ToolExecutor -> filesystem/shell tool -> ToolResult.

No live LLM required. Proves the new tools are reachable through the
exact same real boundary EchoTool already proved in B-004/B-006/B-009
(ToolRegistryAdapter -> ToolExecutorService -> ToolPortAdapter), and
that they are correctly registered in the canonical tool catalog
(core.registry.tool_registry) that Claude A's dynamic-discovery layer
reads from.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.registry.tool_registry import ToolDefinition as CanonicalToolDefinition
from core.registry.tool_registry import ToolRegistry as CanonicalToolRegistry
from infrastructure.persistence.database import create_all_tables, make_engine, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyToolDefinitionRepository

from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.filesystem_tools import (
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.shell_tool import RunCommandTool
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary


def _postgres_available() -> bool:
    try:
        engine = make_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


def _load_tool_registries():
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf))


def test_filesystem_tools_registered_in_canonical_catalog() -> None:
    """Phase 4: registered through the canonical tool-definition/
    registry architecture, not hardcoded into ModelGateway."""
    from core.registry.registry_loader import load_tools

    registry = _load_tool_registries()
    result = load_tools(Path("06_REGISTRIES/data/tools.yaml"), registry)
    assert result.errors == []

    entry = registry.get("filesystem")
    assert isinstance(entry, CanonicalToolDefinition)
    assert entry.verification_status == "verified"
    assert "read_file" in entry.notes
    assert "write_file" in entry.notes


def test_terminal_tool_registered_in_canonical_catalog() -> None:
    from core.registry.registry_loader import load_tools

    registry = _load_tool_registries()
    load_tools(Path("06_REGISTRIES/data/tools.yaml"), registry)

    entry = registry.get("terminal")
    assert entry.verification_status == "verified"
    assert entry.risk_class == "R3"
    assert "run_command" in entry.verification_source


def test_read_file_through_full_tool_boundary(tmp_path: Path) -> None:
    """canonical registration proven above; this proves the actual
    execution path: ToolPort -> ToolExecutor -> real ReadFileTool ->
    real ToolResult, the same boundary EchoTool already proved."""
    (tmp_path / "greeting.txt").write_text("hello from the real filesystem")

    boundary = WorkspaceBoundary(tmp_path)
    executor = ToolExecutorService(ToolRegistryAdapter([ReadFileTool(boundary)]))
    tool_port = ToolPortAdapter(executor, task_id="t1", session_id="s1")

    result = tool_port.execute({"tool_name": "read_file", "args": {"path": "greeting.txt"}})

    assert result["status"] == "ok"
    assert result["result"] == {
        "path": "greeting.txt",
        "content": "hello from the real filesystem",
    }


def test_write_then_list_through_full_tool_boundary(tmp_path: Path) -> None:
    boundary = WorkspaceBoundary(tmp_path)
    executor = ToolExecutorService(
        ToolRegistryAdapter([WriteFileTool(boundary), ListDirectoryTool(boundary)])
    )
    tool_port = ToolPortAdapter(executor, task_id="t1", session_id="s1")

    write_result = tool_port.execute(
        {"tool_name": "write_file", "args": {"path": "out.txt", "content": "data"}}
    )
    assert write_result["status"] == "ok"

    list_result = tool_port.execute({"tool_name": "list_directory", "args": {"path": "."}})
    assert list_result["status"] == "ok"
    assert {"name": "out.txt", "type": "file"} in list_result["result"]["entries"]


def test_boundary_violation_surfaces_as_error_status_not_exception(tmp_path: Path) -> None:
    """TOOL_CONTRACT: execute() never raises for tool-level failures --
    a boundary violation is exactly that class of failure."""
    boundary = WorkspaceBoundary(tmp_path)
    executor = ToolExecutorService(ToolRegistryAdapter([ReadFileTool(boundary)]))
    tool_port = ToolPortAdapter(executor, task_id="t1", session_id="s1")

    result = tool_port.execute({"tool_name": "read_file", "args": {"path": "../../etc/passwd"}})

    assert result["status"] == "error"
    assert "escapes workspace root" in result["error_message"]


def test_run_command_through_full_tool_boundary(tmp_path: Path) -> None:
    import sys

    executor = ToolExecutorService(ToolRegistryAdapter([RunCommandTool(tmp_path, timeout_seconds=5.0)]))
    tool_port = ToolPortAdapter(executor, task_id="t1", session_id="s1")

    result = tool_port.execute(
        {"tool_name": "run_command", "args": {"command": f'{sys.executable} -c "print(2 + 2)"'}}
    )

    assert result["status"] == "ok"
    assert result["result"]["exit_code"] == 0
    assert "4" in result["result"]["stdout"]
