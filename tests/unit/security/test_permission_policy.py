"""Unit tests for the B-012 DefaultPermissionPolicy.

Covers the deny-classified categories from 02_PERMISSION_MODEL.md's
example table, the "ask" categories (denied pending an approval
mechanism that does not exist yet), and allowed baseline behavior.
"""
from __future__ import annotations

import pytest

from neptune.core.contracts.tool_execution import ToolCall
from neptune.infrastructure.security.permission_policy import (
    DefaultPermissionPolicy,
    PermissionDecision,
)


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
def policy() -> DefaultPermissionPolicy:
    return DefaultPermissionPolicy()


# --- non-shell tools: always allowed (table's "edit workspace" row) ---

def test_filesystem_tools_always_allowed(policy: DefaultPermissionPolicy) -> None:
    for tool_name, args in [
        ("read_file", {"path": "a.txt"}),
        ("write_file", {"path": "a.txt", "content": "x"}),
        ("list_directory", {"path": "."}),
    ]:
        verdict = policy.evaluate(make_call(tool_name, args))
        assert verdict.decision == PermissionDecision.ALLOW


def test_ordinary_shell_command_allowed(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(make_call("run_command", {"command": "pytest -q"}))
    assert verdict.decision == PermissionDecision.ALLOW


# --- deny-classified categories ---

def test_delete_remote_branch_denied(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(
        make_call("run_command", {"command": "git push origin --delete feature-x"})
    )
    assert verdict.decision == PermissionDecision.DENY


def test_delete_remote_branch_colon_form_denied(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(
        make_call("run_command", {"command": "git push origin :feature-x"})
    )
    assert verdict.decision == PermissionDecision.DENY


def test_production_migration_denied(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(
        make_call("run_command", {"command": "python manage.py migrate --env production"})
    )
    assert verdict.decision == PermissionDecision.DENY


def test_export_secret_denied(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(
        make_call("run_command", {"command": "cat .env | grep API_KEY"})
    )
    assert verdict.decision == PermissionDecision.DENY


# --- "ask" categories: denied pending approval (no approval flow yet) ---

def test_install_package_denied_pending_approval(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(make_call("run_command", {"command": "pip install requests"}))
    assert verdict.decision == PermissionDecision.DENY_PENDING_APPROVAL


def test_push_branch_denied_pending_approval(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(make_call("run_command", {"command": "git push origin main"}))
    assert verdict.decision == PermissionDecision.DENY_PENDING_APPROVAL


def test_network_access_denied_pending_approval(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(
        make_call("run_command", {"command": "curl https://example.com"})
    )
    assert verdict.decision == PermissionDecision.DENY_PENDING_APPROVAL


def test_deny_pending_approval_is_not_allowed(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(make_call("run_command", {"command": "curl https://example.com"}))
    assert verdict.allowed is False


def test_malformed_command_argument_does_not_crash(policy: DefaultPermissionPolicy) -> None:
    verdict = policy.evaluate(make_call("run_command", {"command": 12345}))
    assert verdict.decision == PermissionDecision.ALLOW
