"""Shell tool unit tests (B-010).

Covers: successful command, non-zero exit, timeout, output limit,
invalid command/input, cwd behavior, result normalization.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from neptune.core.contracts.tool_execution import ToolInputError
from neptune.infrastructure.tools.shell_tool import RunCommandTool


@pytest.fixture
def tool(tmp_path: Path) -> RunCommandTool:
    return RunCommandTool(tmp_path, timeout_seconds=2.0)


def test_successful_command(tool: RunCommandTool) -> None:
    result = tool.execute({"command": f'{sys.executable} -c "print(\'hi\')"'})
    assert result["exit_code"] == 0
    assert "hi" in result["stdout"]
    assert result["timed_out"] is False


def test_non_zero_exit(tool: RunCommandTool) -> None:
    result = tool.execute({"command": f"{sys.executable} -c \"import sys; sys.exit(3)\""})
    assert result["exit_code"] == 3
    assert result["timed_out"] is False


def test_stderr_captured(tool: RunCommandTool) -> None:
    result = tool.execute(
        {"command": f"{sys.executable} -c \"import sys; sys.stderr.write('oops')\""}
    )
    assert "oops" in result["stderr"]


def test_timeout_returns_success_with_timed_out_flag(tool: RunCommandTool) -> None:
    """A command that runs longer than the timeout is a normal,
    informative result -- not a tool-execution failure."""
    result = tool.execute(
        {"command": f"{sys.executable} -c \"import time; time.sleep(10)\""}
    )
    assert result["timed_out"] is True
    assert result["exit_code"] is None


def test_output_truncated_beyond_limit(tool: RunCommandTool) -> None:
    result = tool.execute(
        {"command": f"{sys.executable} -c \"print('x' * 50000)\""}
    )
    assert result["stdout_truncated"] is True
    assert len(result["stdout"]) <= 20_000


def test_invalid_command_reports_nonzero_exit_not_a_python_exception(tool: RunCommandTool) -> None:
    """With shell=True, the shell itself resolves the command and
    reports failure via exit code + stderr -- it does not raise a
    Python-level exception for "command not found." This test proves
    ToolExecutor never has to handle a raw OSError for this case, and
    the tool call still returns a normal, structured result."""
    result = tool.execute({"command": "this_command_does_not_exist_xyz_123"})
    assert result["exit_code"] != 0


def test_command_cwd_is_fixed_to_workspace_root(tool: RunCommandTool, tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    marker.write_text("present")
    # No absolute path given -- if cwd is genuinely fixed to the
    # workspace root, a relative reference resolves there.
    result = tool.execute({"command": f'{sys.executable} -c "print(open(\'marker.txt\').read())"'})
    assert result["exit_code"] == 0
    assert "present" in result["stdout"]


def test_missing_command_argument_raises(tool: RunCommandTool) -> None:
    with pytest.raises(ToolInputError, match="missing required argument: command"):
        tool.execute({})


def test_empty_command_raises(tool: RunCommandTool) -> None:
    with pytest.raises(ToolInputError, match="non-empty string"):
        tool.execute({"command": "   "})


def test_wrong_command_type_raises(tool: RunCommandTool) -> None:
    with pytest.raises(ToolInputError, match="non-empty string"):
        tool.execute({"command": 12345})


def test_definition_has_expected_shape(tool: RunCommandTool) -> None:
    definition = tool.definition()
    assert definition.name == "run_command"
    assert definition.parameters_schema["required"] == ["command"]
