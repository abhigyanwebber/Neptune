"""Filesystem tool unit tests (B-010).

Covers: read, write, list, missing path, invalid path, workspace-
boundary violation, malformed arguments, result normalization.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from neptune.core.contracts.tool_execution import ToolInputError
from neptune.infrastructure.tools.filesystem_tools import (
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary


@pytest.fixture
def boundary(tmp_path: Path) -> WorkspaceBoundary:
    return WorkspaceBoundary(tmp_path)


@pytest.fixture
def read_tool(boundary: WorkspaceBoundary) -> ReadFileTool:
    return ReadFileTool(boundary)


@pytest.fixture
def write_tool(boundary: WorkspaceBoundary) -> WriteFileTool:
    return WriteFileTool(boundary)


@pytest.fixture
def list_tool(boundary: WorkspaceBoundary) -> ListDirectoryTool:
    return ListDirectoryTool(boundary)


# --- write / read round trip ---

def test_write_then_read_round_trip(write_tool: WriteFileTool, read_tool: ReadFileTool) -> None:
    write_result = write_tool.execute({"path": "notes.txt", "content": "hello world"})
    assert write_result == {"path": "notes.txt", "bytes_written": 11}

    read_result = read_tool.execute({"path": "notes.txt"})
    assert read_result == {"path": "notes.txt", "content": "hello world"}


def test_write_creates_parent_directories(write_tool: WriteFileTool, boundary: WorkspaceBoundary) -> None:
    write_tool.execute({"path": "a/b/c/file.txt", "content": "nested"})
    assert (boundary.root / "a" / "b" / "c" / "file.txt").read_text() == "nested"


def test_write_overwrites_existing_file(write_tool: WriteFileTool, read_tool: ReadFileTool) -> None:
    write_tool.execute({"path": "f.txt", "content": "first"})
    write_tool.execute({"path": "f.txt", "content": "second"})
    assert read_tool.execute({"path": "f.txt"})["content"] == "second"


# --- list ---

def test_list_directory_returns_sorted_entries(
    write_tool: WriteFileTool, list_tool: ListDirectoryTool, boundary: WorkspaceBoundary
) -> None:
    write_tool.execute({"path": "b.txt", "content": ""})
    write_tool.execute({"path": "a.txt", "content": ""})
    (boundary.root / "subdir").mkdir()

    result = list_tool.execute({"path": "."})

    assert result["entries"] == [
        {"name": "a.txt", "type": "file"},
        {"name": "b.txt", "type": "file"},
        {"name": "subdir", "type": "dir"},
    ]


def test_list_directory_defaults_to_workspace_root(
    write_tool: WriteFileTool, list_tool: ListDirectoryTool
) -> None:
    write_tool.execute({"path": "only.txt", "content": ""})
    result = list_tool.execute({})
    assert result["entries"] == [{"name": "only.txt", "type": "file"}]


# --- missing path ---

def test_read_missing_file_raises(read_tool: ReadFileTool) -> None:
    with pytest.raises(ToolInputError, match="file not found"):
        read_tool.execute({"path": "does_not_exist.txt"})


def test_list_missing_directory_raises(list_tool: ListDirectoryTool) -> None:
    with pytest.raises(ToolInputError, match="directory not found"):
        list_tool.execute({"path": "no_such_dir"})


# --- invalid path (wrong type) ---

def test_read_a_directory_raises(read_tool: ReadFileTool, boundary: WorkspaceBoundary) -> None:
    (boundary.root / "adir").mkdir()
    with pytest.raises(ToolInputError, match="not a file"):
        read_tool.execute({"path": "adir"})


def test_list_a_file_raises(write_tool: WriteFileTool, list_tool: ListDirectoryTool) -> None:
    write_tool.execute({"path": "afile.txt", "content": "x"})
    with pytest.raises(ToolInputError, match="not a directory"):
        list_tool.execute({"path": "afile.txt"})


def test_write_over_a_directory_raises(write_tool: WriteFileTool, boundary: WorkspaceBoundary) -> None:
    (boundary.root / "adir").mkdir()
    with pytest.raises(ToolInputError, match="is a directory"):
        write_tool.execute({"path": "adir", "content": "x"})


# --- workspace-boundary violation ---

def test_read_path_escaping_workspace_via_dotdot_raises(read_tool: ReadFileTool) -> None:
    with pytest.raises(ToolInputError, match="escapes workspace root"):
        read_tool.execute({"path": "../../etc/passwd"})


def test_read_absolute_path_raises(read_tool: ReadFileTool) -> None:
    """On POSIX, "/etc/passwd" is caught by the explicit is_absolute()
    check. On Windows, a drive-less leading-slash path isn't
    is_absolute() by pathlib's own definition, so it falls through to
    the join+relative_to() escape check instead -- still correctly
    rejected either way, just with a different message, which is what
    this test actually verifies (fails closed, not which message)."""
    with pytest.raises(ToolInputError):
        read_tool.execute({"path": "/etc/passwd"})


def test_read_platform_absolute_path_raises(read_tool: ReadFileTool) -> None:
    """A genuinely is_absolute() path on this platform (drive-letter on
    Windows, leading-slash on POSIX) must hit the explicit early-reject
    check, not just the fallback relative_to() escape check."""
    import os

    platform_absolute = "C:\\Windows\\System32\\config" if os.name == "nt" else "/etc/passwd"
    with pytest.raises(ToolInputError, match="absolute paths are not allowed"):
        read_tool.execute({"path": platform_absolute})


def test_write_path_escaping_workspace_raises(write_tool: WriteFileTool) -> None:
    with pytest.raises(ToolInputError, match="escapes workspace root"):
        write_tool.execute({"path": "../outside.txt", "content": "x"})


def test_list_path_escaping_workspace_raises(list_tool: ListDirectoryTool) -> None:
    with pytest.raises(ToolInputError, match="escapes workspace root"):
        list_tool.execute({"path": "../"})


# --- malformed arguments ---

def test_read_missing_path_argument_raises(read_tool: ReadFileTool) -> None:
    with pytest.raises(ToolInputError, match="missing required argument: path"):
        read_tool.execute({})


def test_write_missing_content_argument_raises(write_tool: WriteFileTool) -> None:
    with pytest.raises(ToolInputError, match="missing required argument: content"):
        write_tool.execute({"path": "f.txt"})


def test_write_wrong_content_type_raises(write_tool: WriteFileTool) -> None:
    with pytest.raises(ToolInputError, match="must be a string"):
        write_tool.execute({"path": "f.txt", "content": 12345})


def test_read_empty_path_raises(read_tool: ReadFileTool) -> None:
    with pytest.raises(ToolInputError, match="non-empty string"):
        read_tool.execute({"path": ""})


def test_list_wrong_path_type_raises(list_tool: ListDirectoryTool) -> None:
    with pytest.raises(ToolInputError, match="must be a string"):
        list_tool.execute({"path": 42})


# --- result normalization / size limits ---

def test_write_oversized_content_raises(write_tool: WriteFileTool) -> None:
    huge = "x" * 300_000
    with pytest.raises(ToolInputError, match="too large"):
        write_tool.execute({"path": "big.txt", "content": huge})


def test_read_oversized_file_raises(write_tool: WriteFileTool, read_tool: ReadFileTool, boundary: WorkspaceBoundary) -> None:
    (boundary.root / "big.txt").write_text("x" * 300_000)
    with pytest.raises(ToolInputError, match="too large"):
        read_tool.execute({"path": "big.txt"})


def test_read_non_utf8_file_raises(read_tool: ReadFileTool, boundary: WorkspaceBoundary) -> None:
    (boundary.root / "binary.dat").write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(ToolInputError, match="not valid UTF-8"):
        read_tool.execute({"path": "binary.dat"})


def test_definitions_have_expected_shape(
    read_tool: ReadFileTool, write_tool: WriteFileTool, list_tool: ListDirectoryTool
) -> None:
    for tool, name in [(read_tool, "read_file"), (write_tool, "write_file"), (list_tool, "list_directory")]:
        definition = tool.definition()
        assert definition.name == name
        assert definition.parameters_schema["type"] == "object"
