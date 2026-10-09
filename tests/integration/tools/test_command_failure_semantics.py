"""Command-failure semantics (MVP closure, Review 009).

A tool that ran but reports a failed command (non-zero exit_code, or
timed_out) must be a FAILED execution, never SUCCESS -- otherwise the
observation says status "ok", RuntimeDriver keeps going, and a step can be
reported as succeeded when its command failed. Real RunCommandTool for real
exit codes; a minimal stub only for timed_out, to avoid waiting on a real
timeout.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from neptune.core.contracts.tool_execution import ToolCall, ToolDefinition, ToolOutcome
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.filesystem_tools import ReadFileTool, WriteFileTool
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.shell_tool import RunCommandTool
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary


def make_call(tool_name: str, arguments: dict) -> ToolCall:
    return ToolCall(
        call_id="call-1", tool_name=tool_name, arguments=arguments,
        task_id="task-1", session_id="session-1", turn_id="turn-1",
    )


@pytest.fixture
def executor(tmp_path: Path) -> ToolExecutorService:
    boundary = WorkspaceBoundary(tmp_path)
    registry = ToolRegistryAdapter(
        [ReadFileTool(boundary), WriteFileTool(boundary), RunCommandTool(boundary.root)]
    )
    return ToolExecutorService(registry, timeout_seconds=10.0)


def test_successful_command_is_success(executor: ToolExecutorService) -> None:
    result = executor.execute(make_call("run_command", {"command": "echo hello"}))
    assert result.outcome == ToolOutcome.SUCCESS
    assert result.error_message is None
    assert result.output["exit_code"] == 0


def test_nonzero_exit_is_a_failed_execution_with_evidence_kept(executor: ToolExecutorService) -> None:
    result = executor.execute(make_call("run_command", {"command": "exit 3"}))
    assert result.outcome == ToolOutcome.ERROR
    assert result.error_message == "command exited with code 3"
    # The output is preserved, so the model/user still see what happened.
    assert result.output["exit_code"] == 3


def test_filesystem_tools_are_unaffected(executor: ToolExecutorService, tmp_path: Path) -> None:
    written = executor.execute(make_call("write_file", {"path": "a.txt", "content": "x"}))
    assert written.outcome == ToolOutcome.SUCCESS
    read = executor.execute(make_call("read_file", {"path": "a.txt"}))
    assert read.outcome == ToolOutcome.SUCCESS


class _TimedOutTool:
    name = "slow"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="slow", description="stub", parameters_schema={})

    def execute(self, arguments: dict) -> dict:
        return {"stdout": "", "stderr": "", "exit_code": None, "timed_out": True, "timeout_seconds": 7}


def test_timed_out_command_is_a_timeout_not_success() -> None:
    executor = ToolExecutorService(ToolRegistryAdapter([_TimedOutTool()]), timeout_seconds=5.0)
    result = executor.execute(make_call("slow", {}))
    assert result.outcome == ToolOutcome.TIMEOUT
    assert "timed out" in result.error_message
    assert result.output["timed_out"] is True


def test_observation_for_a_failed_command_has_status_error(executor: ToolExecutorService) -> None:
    """The boundary RuntimeDriver actually reads: ToolPortAdapter must turn
    the failed command into status 'error' (which stops the loop), while a
    successful command stays 'ok'."""
    port = ToolPortAdapter(executor, task_id="task-1", session_id="session-1")
    failed = port.execute({"tool_name": "run_command", "args": {"command": "exit 3"}})
    assert failed["status"] == "error"
    assert failed["outcome"] == "error"
    assert "exited with code 3" in failed["error_message"]

    ok = port.execute({"tool_name": "run_command", "args": {"command": "echo hello"}})
    assert ok["status"] == "ok"
