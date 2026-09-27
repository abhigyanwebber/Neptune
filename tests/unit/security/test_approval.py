"""Unit tests for B-013 approval provider implementations."""
from __future__ import annotations

import pytest

from neptune.core.contracts.tool_execution import ToolCall
from neptune.infrastructure.security.approval import (
    ApprovalDecision,
    ApprovalError,
    AutoRejectApprovalProvider,
    FailingApprovalProvider,
    StaticApprovalProvider,
)
from neptune.infrastructure.security.permission_policy import (
    PermissionDecision,
    PermissionVerdict,
)


def make_call() -> ToolCall:
    return ToolCall(
        call_id="c1",
        tool_name="run_command",
        arguments={"command": "curl https://example.com"},
        task_id="t1",
        session_id="s1",
        turn_id="tu1",
    )


def make_ask_verdict() -> PermissionVerdict:
    return PermissionVerdict(PermissionDecision.ASK, "network access")


def test_auto_reject_always_rejects() -> None:
    provider = AutoRejectApprovalProvider()
    assert provider.decide(make_call(), make_ask_verdict()) == ApprovalDecision.REJECTED


def test_failing_provider_raises_approval_error() -> None:
    provider = FailingApprovalProvider()
    with pytest.raises(ApprovalError):
        provider.decide(make_call(), make_ask_verdict())


def test_static_provider_default() -> None:
    provider = StaticApprovalProvider(default=ApprovalDecision.APPROVED)
    assert provider.decide(make_call(), make_ask_verdict()) == ApprovalDecision.APPROVED


def test_static_provider_per_tool_override() -> None:
    provider = StaticApprovalProvider(
        default=ApprovalDecision.REJECTED,
        overrides={"run_command": ApprovalDecision.APPROVED},
    )
    assert provider.decide(make_call(), make_ask_verdict()) == ApprovalDecision.APPROVED
