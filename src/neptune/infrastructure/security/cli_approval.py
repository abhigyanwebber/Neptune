"""Human approval over a terminal (MVP, T3).

Implements the existing ApprovalProvider Protocol (B-013); adds no new
permission concept. ToolExecutorService still evaluates the policy first
and only consults this provider for an ASK verdict, strictly before
dispatch -- this class only answers approved/rejected.

Fails closed: anything other than an explicit "y"/"yes" is a rejection,
and an unavailable input channel (EOF, e.g. no terminal attached) raises
ApprovalError, which the executor treats as not-approved. Ctrl-C is not
swallowed; it aborts the whole run as the user intended.

`ask` and `out` are injectable so tests drive it without a terminal.
"""
from __future__ import annotations

from typing import Callable

from neptune.core.contracts.tool_execution import ToolCall
from neptune.infrastructure.security.approval import ApprovalDecision, ApprovalError
from neptune.infrastructure.security.permission_policy import PermissionVerdict

_MAX_ARG_CHARS = 2000


class CliApprovalProvider:
    def __init__(
        self,
        ask: Callable[[str], str] = input,
        out: Callable[[str], None] = print,
    ) -> None:
        self._ask = ask
        self._out = out

    def decide(self, call: ToolCall, verdict: PermissionVerdict) -> ApprovalDecision:
        self._out("")
        self._out("APPROVAL REQUIRED")
        self._out(f"  tool:   {call.tool_name}")
        for key, value in (call.arguments or {}).items():
            text = str(value)
            if len(text) > _MAX_ARG_CHARS:
                text = text[:_MAX_ARG_CHARS] + f"... [truncated, {len(str(value))} chars total]"
            self._out(f"  {key}: {text}")
        self._out(f"  reason: {verdict.reason}")
        try:
            answer = self._ask("Approve this action? [y/N]: ")
        except EOFError as exc:
            raise ApprovalError("no input channel available for approval") from exc
        if answer.strip().lower() in ("y", "yes"):
            return ApprovalDecision.APPROVED
        return ApprovalDecision.REJECTED
