# DIRECTOR_REVIEW_006B — B-013 Permission ASK / Approval Mechanism

## 1. Status

Complete. Implemented on `worker/claude-b`, all required cases proven,
full suite passing, no regressions.

## 2. Existing permission architecture (as of B-012)

`DefaultPermissionPolicy.evaluate(call) -> PermissionVerdict` runs
inside `ToolExecutorService.execute()`, after tool lookup and strictly
before `tool.execute()`. B-012 represented only two outcomes at
runtime -- ALLOW and DENY -- because the table's "ask" rows (install
package, push branch, network access) had nowhere to go: `PERMISSION_DECISION`
had a `DENY_PENDING_APPROVAL` member that was, in practice, just DENY
with a different label.

## 3. ASK gap

B-012's own report named this directly: "ask" rows have no approval
mechanism in this codebase, so they were denied outright. That is the
exact gap B-013 closes -- ASK needed to become a real third path
(`policy -> ASK -> approval provider -> allow/deny -> ToolExecutor`),
not a permanent synonym for DENY.

## 4. Approval seam selected

Inside `ToolExecutorService.execute()`, immediately after
`PermissionPolicy.evaluate()`, exactly where the ASK branch is
distinguished from DENY: `PermissionDecision` now has three members
(ALLOW / DENY / ASK). When the verdict is ASK, the executor calls a
new `ApprovalProvider.decide(call, verdict) -> ApprovalDecision`
(APPROVED/REJECTED, may raise `ApprovalError`). No second registry,
no second `ToolCall`/`ToolExecutor` contract -- the approval provider
only ever answers approved/rejected for a verdict the existing policy
already produced, and an approved ASK falls through into the exact
same `tool.execute()` call an ALLOW would use.

## 5. Files changed

- `src/neptune/infrastructure/security/permission_policy.py` --
  `PermissionDecision.DENY_PENDING_APPROVAL` replaced with `ASK`.
- `src/neptune/infrastructure/security/approval.py` (new) --
  `ApprovalDecision`, `ApprovalError`, `ApprovalProvider` Protocol,
  `AutoRejectApprovalProvider` (production default, fails closed),
  `FailingApprovalProvider` and `StaticApprovalProvider` (test doubles).
- `src/neptune/infrastructure/tools/executor.py` -- `ToolExecutorService`
  takes an optional `approval_provider`; ASK verdicts are routed
  through it before dispatch.
- `tests/unit/security/test_permission_policy.py` -- updated for the
  ASK rename (behavior unchanged).
- `tests/unit/security/test_approval.py` (new) -- provider unit tests.
- `tests/integration/security/test_ask_approval.py` (new) -- the five
  required end-to-end cases.

No files outside `src/neptune/infrastructure/{security,tools}` and
`tests/{unit,integration}/security` were touched. No planning/runtime/
gateway/registry files, no A-011 files, no shared bookkeeping files.

## 6. ALLOW proof

`test_case1_allow_ordinary_command_executes` -- an ordinary command
(`echo hello`) still runs and returns SUCCESS, unchanged from B-012.

## 7. DENY proof

`test_case2_deny_never_reaches_tool` -- a deny-classified command
(`git push origin --delete x`) is denied and a marker file the command
string would also have written is never created, proving the shell
never ran.

## 8. ASK -> APPROVE proof

`test_case3_ask_approved_reaches_real_tool` -- an ask-classified
command (`curl --version`) with `StaticApprovalProvider(APPROVED)`
returns SUCCESS and a marker file written by the same command string
exists on disk, proving real execution through the normal
`ToolExecutor` path (not a second route).

## 9. ASK -> DENY proof

`test_case4_ask_rejected_never_reaches_tool` -- the same command with
`StaticApprovalProvider(REJECTED)` returns DENIED and the marker file
is absent.

## 10. Approval-failure proof

`test_case5_approval_failure_fails_closed` -- `FailingApprovalProvider`
raises `ApprovalError`; the executor catches it and returns DENIED,
marker absent. `test_default_executor_fails_closed_on_ask_with_no_provider_configured`
additionally proves the production default (no provider passed at all)
also denies ASK, since `AutoRejectApprovalProvider` is the default.

## 11. Security limitations

- Shell restriction is still the B-012 regex heuristic on the command
  string; approval does not make it a complete guarantee, and this
  task did not redesign it (out of scope, per instructions).
- No real approval channel exists (no human-in-the-loop UI, no
  external service) -- `AutoRejectApprovalProvider` is the only
  production-wired implementation today, so ASK currently still
  behaves as deny-by-default in practice. The difference from B-012 is
  architectural: ASK is now explicitly represented and routed through
  a replaceable seam, not silently folded into DENY.
- No sandboxing, as required.

## 12. Test results

New: 12 tests (5 unit approval-provider, 7 integration ask-approval).
Updated: 4 existing unit tests renamed (ASK instead of
DENY_PENDING_APPROVAL), behavior unchanged.

Focused run (security + B-012 tool-permission tests): 24 passed, 0
failed.

Full suite: 329 passed, 7 skipped, 0 failed. (Skip count differs from
B-012's report of 37 skipped; this is environmental -- e.g. DB/live
fixtures now available/unavailable in this run -- not caused by this
change; no test newly skips or fails because of B-013.)

## 13. Architectural impact

Minimal, additive extension of the existing TOOL_CONTRACT execution
boundary: one new enum member value swap (no new `ToolOutcome`
needed -- ASK-rejected and DENY both still report
`ToolOutcome.DENIED`, distinguished by `error_message`), one new
optional constructor parameter on `ToolExecutorService`, one new small
module (`approval.py`) defining the seam. No changes to `ToolCall`,
`ToolOutcome`, `ToolExecutor` Protocol, `ToolPortAdapter`, or any
Runtime/Planning/Gateway code.

## 14. Out-of-scope confirmation

Not touched: `GoalPlanner`, `Plan`, `PlanExecutor`, `AgentRuntime`,
`RuntimeDriver`, `ModelGateway`, `ToolOfferingResolver`, tool registry
architecture, any A-011 files, `DEVELOPMENT_STATE/assignments.yaml`,
`DEVELOPMENT_STATE/decisions.yaml`, `DEVELOPMENT_STATE/workers.yaml`,
`05_DECISIONS/00_ADR_INDEX.md`. No UI, no server, no auth, no
multi-user approval, no sandboxing/container/OS/network isolation
were built.

## 15. Known limitations

- Deny-by-default in practice for ASK until a real approval channel
  (human-in-the-loop, external service, etc.) is built and wired in as
  the `approval_provider`.
- Shell command matching remains heuristic/evadable (B-012's existing,
  documented limitation).
- `StaticApprovalProvider` exists only as a test/proof double, not a
  production mechanism.

## 16. Recommended next step

Director decides whether/when to build a real approval channel
(human-in-the-loop prompt, external approval service, etc.) as a
concrete `ApprovalProvider` implementation. No new ADR is proposed by
this task -- the approval seam is an implementation detail of the
already-frozen `02_PERMISSION_MODEL.md` design, not a new
architectural decision -- but if the director wants a formal record of
the ASK/DENY-vs-approval-failure distinction, a short ADR title such
as "Approval boundary for the permission ASK tier" would be the
natural candidate, left for director numbering.
