"""Approval abstraction for the ASK permission tier (B-013).

Smallest seam that lets ToolExecutorService obtain an explicit
approved/rejected decision for a ToolCall the policy classified as
ASK, without becoming a second authorization system: the approval
provider only ever answers "approved" or "rejected" for a verdict
PermissionPolicy already produced -- it does not itself decide
ALLOW/DENY/ASK, and it is consulted strictly after policy evaluation
and strictly before ToolExecutorService dispatches to the tool.

No UI, no server, no auth, no multi-user routing -- out of scope per
B-013. This module defines the boundary (ApprovalProvider Protocol)
and two minimal, deterministic implementations: one that fails closed
(the production default, since no real approval channel exists yet)
and one a test can configure explicitly per-call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from neptune.core.contracts.tool_execution import ToolCall
from neptune.infrastructure.security.permission_policy import PermissionVerdict


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalError(Exception):
    """Raised by an ApprovalProvider when a decision could not be
    obtained at all (channel unavailable, timeout, etc.) -- distinct
    from returning REJECTED, which is a real decision. The executor
    boundary must treat both as "do not execute" (fail closed); this
    type exists so a provider can be honest about the difference
    without weakening that guarantee."""


@runtime_checkable
class ApprovalProvider(Protocol):
    def decide(self, call: ToolCall, verdict: PermissionVerdict) -> ApprovalDecision:
        """Return APPROVED or REJECTED for an ASK verdict. May raise
        ApprovalError if no decision could be obtained; callers must
        treat that the same as REJECTED (fail closed)."""
        ...


class AutoRejectApprovalProvider:
    """Production default. No real approval channel exists yet (no
    human-in-the-loop, no external service), so the only honest,
    fail-closed implementation is one that always rejects -- this
    preserves exactly the deny-by-default behavior B-012 already had
    for the "ask" tier, but now expressed through the explicit
    approval seam instead of the policy layer pretending ASK is DENY.
    """

    def decide(self, call: ToolCall, verdict: PermissionVerdict) -> ApprovalDecision:
        return ApprovalDecision.REJECTED


class FailingApprovalProvider:
    """Test/proof double: simulates the approval channel itself being
    unavailable (raises ApprovalError rather than returning a
    decision). Used to prove the executor fails closed when approval
    cannot be obtained at all, not just when it is actively rejected.
    """

    def decide(self, call: ToolCall, verdict: PermissionVerdict) -> ApprovalDecision:
        raise ApprovalError("approval channel unavailable")


@dataclass
class StaticApprovalProvider:
    """Deterministic test double: returns a fixed decision for every
    ASK call, or per-tool_name overrides. Matches the task's allowance
    for "a deterministic/test approval provider if that matches the
    existing architecture" -- this codebase already uses fixed/fake
    doubles for its other Protocol boundaries (e.g. FakeToolPort), so
    this follows the same pattern rather than inventing a new one.
    """

    default: ApprovalDecision = ApprovalDecision.REJECTED
    overrides: dict[str, ApprovalDecision] = field(default_factory=dict)

    def decide(self, call: ToolCall, verdict: PermissionVerdict) -> ApprovalDecision:
        return self.overrides.get(call.tool_name, self.default)
