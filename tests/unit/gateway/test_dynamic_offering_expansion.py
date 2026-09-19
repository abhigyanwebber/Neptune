"""Unit tests: dynamic-offering catalog-to-concrete-tool expansion
(B-011 finding, see model_gateway_adapter.py module docstring).

Covers: known catalog families (filesystem, terminal) expand into
real, schema'd ToolDefinitions; unknown/unbacked catalog entries
(browser, mcp, search) keep A-008's original degraded 1:1 translation
unchanged; concrete_tool_definitions absent still works without error.
"""
from __future__ import annotations

from neptune.core.contracts.model_gateway import ToolDefinition
from neptune.infrastructure.gateway.model_gateway_adapter import (
    _offering_dicts_to_tool_definitions,
)
from neptune.infrastructure.tools.filesystem_tools import (
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from neptune.infrastructure.tools.shell_tool import RunCommandTool
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary


def _filesystem_offering() -> dict:
    return {"tool_id": "filesystem", "name": "Filesystem", "description": "File read/write/list", "capability": "tool_use"}


def _terminal_offering() -> dict:
    return {"tool_id": "terminal", "name": "Terminal", "description": "Shell execution", "capability": "terminal"}


def _mcp_offering() -> dict:
    return {"tool_id": "mcp", "name": "MCP", "description": "Model Context Protocol", "capability": "mcp"}


def _concrete_fs_definitions(tmp_path) -> dict[str, ToolDefinition]:
    boundary = WorkspaceBoundary(tmp_path)
    tools = [ReadFileTool(boundary), WriteFileTool(boundary), ListDirectoryTool(boundary)]
    return {t.name: t.definition() for t in tools}


def _concrete_shell_definitions(tmp_path) -> dict[str, ToolDefinition]:
    tool = RunCommandTool(tmp_path)
    return {tool.name: tool.definition()}


def test_filesystem_offering_expands_to_three_real_tool_definitions(tmp_path) -> None:
    concrete = _concrete_fs_definitions(tmp_path)
    result = _offering_dicts_to_tool_definitions([_filesystem_offering()], concrete)

    names = {d.name for d in result}
    assert names == {"read_file", "write_file", "list_directory"}
    # Each expanded definition has a real, non-empty argument schema --
    # this is exactly the gap the fix closes.
    for d in result:
        assert d.parameters_schema.get("properties")


def test_terminal_offering_expands_to_run_command(tmp_path) -> None:
    concrete = {**_concrete_fs_definitions(tmp_path), **_concrete_shell_definitions(tmp_path)}
    result = _offering_dicts_to_tool_definitions([_terminal_offering()], concrete)

    assert [d.name for d in result] == ["run_command"]
    assert result[0].parameters_schema["required"] == ["command"]


def test_both_offerings_expand_together(tmp_path) -> None:
    concrete = {**_concrete_fs_definitions(tmp_path), **_concrete_shell_definitions(tmp_path)}
    result = _offering_dicts_to_tool_definitions(
        [_filesystem_offering(), _terminal_offering()], concrete
    )
    assert {d.name for d in result} == {"read_file", "write_file", "list_directory", "run_command"}


def test_unbacked_catalog_entry_falls_back_to_degraded_translation_unchanged() -> None:
    """mcp/search/browser have no real Tool implementation yet -- this
    is A-008's original behavior and must remain unchanged: offering
    name used as the ToolDefinition name, empty schema, nothing
    dropped or hidden."""
    result = _offering_dicts_to_tool_definitions([_mcp_offering()], concrete_by_name={})
    assert len(result) == 1
    assert result[0].name == "mcp"
    assert result[0].parameters_schema == {}


def test_missing_concrete_definition_for_known_family_is_skipped_not_crashed(tmp_path) -> None:
    """If the caller declares a known family but didn't actually pass
    the concrete definition (e.g. only gave read_file, not write_file/
    list_directory), expansion includes only what's available rather
    than raising -- a caller-side wiring gap should degrade gracefully,
    not crash the whole request."""
    boundary = WorkspaceBoundary(tmp_path)
    partial_concrete = {"read_file": ReadFileTool(boundary).definition()}

    result = _offering_dicts_to_tool_definitions([_filesystem_offering()], partial_concrete)

    assert [d.name for d in result] == ["read_file"]


def test_empty_offerings_list_returns_empty() -> None:
    assert _offering_dicts_to_tool_definitions([], {}) == []
