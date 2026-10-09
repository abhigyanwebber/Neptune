"""B-013 integration proof: the ASK permission tier routes through an
explicit approval boundary before ToolExecutorService dispatches to a
tool. Proves all five required cases with real tool execution/marker
side effects, not just returned enums (per task requirement).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from neptune.core.contracts.tool_execution import ToolCall, ToolOutcome
from neptune.infrastructure.security.approval import (
    ApprovalDecision,
    FailingApprovalProvider,
    StaticApprovalProvider,
)
from neptune.infrastructure.tools.executor import ToolExecutorService
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


def make_executor(workspace: WorkspaceBoundary, approval_provider=None) -> ToolExecutorService:
    registry = ToolRegistryAdapter([RunCommandTool(workspace.root)])
    return ToolExecutorService(registry, timeout_seconds=5.0, approval_provider=approval_provider)


def test_case1_allow_ordinary_command_executes(workspace: WorkspaceBoundary) -> None:
    executor = make_executor(workspace)
    result = executor.execute(make_call("run_command", {"command": "echo hello"}))
    assert result.outcome == ToolOutcome.SUCCESS
    assert "hello" in result.output["stdout"]


def test_case2_deny_never_reaches_tool(workspace: WorkspaceBoundary) -> None:
    executor = make_executor(workspace)
    marker = workspace.root / "case2-marker.txt"
    result = executor.execute(
        make_call(
            "run_command",
            {"command": f"git push origin --delete x; echo ran > {marker}"},
        )
    )
    assert result.outcome == ToolOutcome.DENIED
    assert not marker.exists()


def test_case3_ask_approved_reaches_real_tool(workspace: WorkspaceBoundary) -> None:
    approval_provider = StaticApprovalProvider(default=ApprovalDecision.APPROVED)
    executor = make_executor(workspace, approval_provider=approval_provider)
    marker = workspace.root / "case3-marker.txt"
    result = executor.execute(
        make_call(
            "run_command",
            {"command": f"curl --version && echo ran > {marker}"},
        )
    )
    assert result.outcome == ToolOutcome.SUCCESS
    assert marker.exists(), "approved ASK must reach the real tool"


def test_case4_ask_rejected_never_reaches_tool(workspace: WorkspaceBoundary) -> None:
    approval_provider = StaticApprovalProvider(default=ApprovalDecision.REJECTED)
    executor = make_executor(workspace, approval_provider=approval_provider)
    marker = workspace.root / "case4-marker.txt"
    result = executor.execute(
        make_call(
            "run_command",
            {"command": f"curl --version; echo ran > {marker}"},
        )
    )
    assert result.outcome == ToolOutcome.DENIED
    assert not marker.exists(), "rejected ASK must never reach the real tool"


def test_case5_approval_failure_fails_closed(workspace: WorkspaceBoundary) -> None:
    executor = make_executor(workspace, approval_provider=FailingApprovalProvider())
    marker = workspace.root / "case5-marker.txt"
    result = executor.execute(
        make_call(
            "run_command",
            {"command": f"curl --version; echo ran > {marker}"},
        )
    )
    assert result.outcome == ToolOutcome.DENIED
    assert not marker.exists(), "a failed approval channel must never execute the tool"


def test_default_executor_fails_closed_on_ask_with_no_provider_configured(
    workspace: WorkspaceBoundary,
) -> None:
    # No approval_provider passed -- exercises AutoRejectApprovalProvider,
    # the production default, proving deny-by-default is preserved even
    # when nobody wires up an approval channel at all.
    executor = make_executor(workspace)
    result = executor.execute(make_call("run_command", {"command": "curl --version"}))
    assert result.outcome == ToolOutcome.DENIED

