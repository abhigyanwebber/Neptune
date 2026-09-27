"""B-012 integration proof: ToolExecutorService denies unsafe shell
commands before they reach RunCommandTool.execute(), and authorized
operations (filesystem + ordinary shell) still flow through exactly
as B-010/B-011 proved. No live model/provider required (per B-012
task scope: "a non-live integration test is sufficient for the core
security proof").
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from neptune.core.contracts.tool_execution import ToolCall, ToolOutcome
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.filesystem_tools import ReadFileTool, WriteFileTool
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.shell_tool import RunCommandTool
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary


def make_call(tool_name: str, arguments: dict) -> ToolCall:
    return ToolCall(
        call_id="call-1",
        tool_name=tool_name,
        arguments=arguments,
        task_id="task-1",
        session_id="session-1",
        turn_id="turn-1",
    )


@pytest.fixture
def workspace(tmp_path: Path) -> WorkspaceBoundary:
    return WorkspaceBoundary(tmp_path)


@pytest.fixture
def executor(workspace: WorkspaceBoundary) -> ToolExecutorService:
    registry = ToolRegistryAdapter(
        [
            ReadFileTool(workspace),
            WriteFileTool(workspace),
            RunCommandTool(workspace.root),
        ]
    )
    return ToolExecutorService(registry, timeout_seconds=5.0)


def test_denied_delete_remote_branch_never_executes(
    executor: ToolExecutorService, workspace: WorkspaceBoundary
) -> None:
    # Uses a marker file the "unsafe" command would touch if it ran --
    # proves absence of the side effect, not just a denied verdict.
    marker = workspace.root / "marker.txt"
    call = make_call(
        "run_command",
        {"command": f"git push origin --delete x; echo ran > {marker}"},
    )
    result = executor.execute(call)

    assert result.outcome == ToolOutcome.DENIED
    assert not marker.exists(), "denied command must never reach the shell"


def test_denied_export_secret_returns_structured_result(
    executor: ToolExecutorService,
) -> None:
    result = executor.execute(
        make_call("run_command", {"command": "cat .env | grep API_KEY"})
    )
    assert result.outcome == ToolOutcome.DENIED
    assert result.error_message is not None
    assert "secret" in result.error_message.lower()


def test_denied_push_pending_approval_is_structured_not_crash(
    executor: ToolExecutorService,
) -> None:
    result = executor.execute(make_call("run_command", {"command": "git push origin main"}))
    assert result.outcome == ToolOutcome.DENIED
    assert "approval" in result.error_message.lower()


def test_ordinary_shell_command_still_executes(executor: ToolExecutorService) -> None:
    result = executor.execute(make_call("run_command", {"command": "echo hello"}))
    assert result.outcome == ToolOutcome.SUCCESS
    assert "hello" in result.output["stdout"]


def test_filesystem_write_then_read_still_authorized(
    executor: ToolExecutorService,
) -> None:
    write_result = executor.execute(
        make_call("write_file", {"path": "note.txt", "content": "hi"})
    )
    assert write_result.outcome == ToolOutcome.SUCCESS

    read_result = executor.execute(make_call("read_file", {"path": "note.txt"}))
    assert read_result.outcome == ToolOutcome.SUCCESS
    assert read_result.output["content"] == "hi"
