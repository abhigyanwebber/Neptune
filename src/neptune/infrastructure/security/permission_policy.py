"""Minimum tool-boundary permission enforcement (B-012).

Implements the smallest enforceable slice of the frozen design in
07_SECURITY/02_PERMISSION_MODEL.md: a Policy decision ("what the
system permits an actor to request") evaluated per ToolCall, before
ToolExecutorService dispatches to the tool's own execute(). This is
NOT Sandbox (07_SECURITY/01_THREAT_MODEL.md's SANDBOX_CONTRACT stays
frozen/unimplemented -- no process/container isolation here) and it
is NOT Approval (no human-in-the-loop mechanism exists in this
codebase yet).

02_PERMISSION_MODEL.md's example policy table has three tiers:
allow, ask, deny. Only two are enforceable without an approval
mechanism:
  - allow: unconditionally allowed (filesystem read/edit, running
    commands in general -- matches "read repository" / "edit
    workspace" / "run tests" in the table).
  - deny: unconditionally blocked (matches "delete remote branch",
    "production migration", "export secret").
"ask" rows (install package, network access, push branch) have no
home yet -- there is no approval workflow to route them through. Per
02_PERMISSION_MODEL.md's precedence (EXPLICIT APPROVAL sits above
ALLOW RULE, not below it), an action that requires approval must not
silently fall through to plain allow just because approval isn't
implemented. This policy therefore denies "ask" categories for now,
labelled distinctly from a hard "deny" row so the gap is visible
rather than hidden. See the final B-012 report for this as a named
limitation, not a silent design choice.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from neptune.core.contracts.tool_execution import ToolCall


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    DENY_PENDING_APPROVAL = "deny_pending_approval"


@dataclass(frozen=True)
class PermissionVerdict:
    decision: PermissionDecision
    reason: str

    @property
    def allowed(self) -> bool:
        return self.decision == PermissionDecision.ALLOW


@runtime_checkable
class PermissionPolicy(Protocol):
    def evaluate(self, call: ToolCall) -> PermissionVerdict:
        ...


# --- Deny-classified categories (02_PERMISSION_MODEL.md example table) ---
# Best-effort substring/regex matching on the shell command string.
# This is explicitly heuristic, not a security guarantee: a
# sufficiently obfuscated command can still evade it (matches this
# file's own limitation note and 01_THREAT_MODEL.md's existing
# acknowledgement that real isolation is deferred, not built here).
# Kept intentionally small and named after the exact table rows --
# no speculative categories invented beyond what 02_PERMISSION_MODEL.md
# already lists.
_DELETE_REMOTE_BRANCH = re.compile(
    r"git\s+push\s+.*--delete\b|git\s+push\s+\S+\s+:\S+"
)
_PRODUCTION_MIGRATION = re.compile(
    r"\bprod(uction)?\b.*\bmigrat(e|ion)\b|\bmigrat(e|ion)\b.*\bprod(uction)?\b",
    re.IGNORECASE,
)
_EXPORT_SECRET = re.compile(
    r"\b(cat|printenv|echo)\b[^\n]*\b(SECRET|API_KEY|TOKEN|PASSWORD|PRIVATE_KEY)\b",
    re.IGNORECASE,
)

# --- "ask" categories with no approval mechanism yet (see module docstring) ---
_INSTALL_PACKAGE = re.compile(r"\b(pip|npm|yarn|pnpm|apt(-get)?|choco|winget)\s+install\b")
_PUSH_BRANCH = re.compile(r"git\s+push\b")
_NETWORK_ACCESS = re.compile(r"\b(curl|wget|Invoke-WebRequest|iwr)\b")

_DENY_RULES: list[tuple[re.Pattern, str]] = [
    (_DELETE_REMOTE_BRANCH, "delete remote branch (deny per 02_PERMISSION_MODEL.md)"),
    (_PRODUCTION_MIGRATION, "production migration (deny per 02_PERMISSION_MODEL.md)"),
    (_EXPORT_SECRET, "export secret (deny per 02_PERMISSION_MODEL.md)"),
]

_ASK_RULES: list[tuple[re.Pattern, str]] = [
    (_INSTALL_PACKAGE, "install package"),
    (_PUSH_BRANCH, "push branch"),
    (_NETWORK_ACCESS, "network access"),
]


class DefaultPermissionPolicy:
    """Reference PermissionPolicy. Secure-by-default: unrecognized
    tools/commands are allowed (matches the table's default rows for
    "read repository" / "edit workspace" / "run tests"), only the
    named deny/ask categories above are blocked.
    """

    #: tool_name -> True if this tool's calls are shell commands that
    #: need the command-pattern rules; filesystem tools (read_file,
    #: write_file, list_directory) match the table's "edit workspace"
    #: row (allow) and are not inspected further -- WorkspaceBoundary
    #: (B-010) already enforces their real boundary (path escape).
    _SHELL_TOOLS = {"run_command"}

    def evaluate(self, call: ToolCall) -> PermissionVerdict:
        if call.tool_name not in self._SHELL_TOOLS:
            return PermissionVerdict(PermissionDecision.ALLOW, "not a shell tool")

        command = call.arguments.get("command")
        if not isinstance(command, str):
            # Malformed input -- let the tool's own ToolInputError
            # validation handle this; the permission layer only
            # rejects for its own reasons, not everything malformed.
            return PermissionVerdict(PermissionDecision.ALLOW, "no command to evaluate")

        for pattern, label in _DENY_RULES:
            if pattern.search(command):
                return PermissionVerdict(PermissionDecision.DENY, label)

        for pattern, label in _ASK_RULES:
            if pattern.search(command):
                return PermissionVerdict(
                    PermissionDecision.DENY_PENDING_APPROVAL,
                    f"{label} (requires approval; no approval workflow implemented yet)",
                )

        return PermissionVerdict(PermissionDecision.ALLOW, "no matching restriction")
