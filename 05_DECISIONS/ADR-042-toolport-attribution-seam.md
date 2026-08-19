# ADR-042 — ToolPort Attribution Seam (B-006 Finding)

**Status:** PROPOSED

## Context
B-006 required proving that real tool-execution state survives a
process restart using existing Runtime/Driver/ToolExecution/
Observation/Checkpoint/Registry infrastructure. Doing so required, for
the first time, running Claude A's Core Runtime (`worker/claude-a`)
and Claude B's Tool Execution Boundary (`worker/claude-b`, B-004)
together in one process -- these two lanes had been built against
each other's *contracts* but never actually integrated end-to-end
before this task.

## Decision
`core.contracts.tools.ToolPort.execute(tool_call: dict) -> dict` is,
by design (its own docstring), opaque from Core's point of view: the
`tool_call` dict Core Runtime passes in is just
`{"tool_name": ..., "args": ...}` -- no `task_id`, `session_id`, or
`turn_id`.

Neptune's own `ToolCall` (TOOL_CONTRACT, B-004) *requires*
`task_id`/`session_id`/`turn_id` as part of invariant 2: "external
side effects are attributable to a task/session/agent."

These two requirements do not contradict each other, but they do not
connect automatically either. The fix is a thin adapter --
`neptune.infrastructure.tools.tool_port_adapter.ToolPortAdapter` --
constructed once per Runtime/process with the `task_id` and a
`session_id` hint already known at that point, which supplies the
attribution context on Neptune's side for every opaque call Core
sends it. `turn_id` has no equivalent passed through `ToolPort` at
all, so the adapter uses a placeholder (`"{session_id}-pending-turn"`)
purely to satisfy `ToolCall`'s required field -- it carries no
functional meaning and is not used for routing, dedup, or any other
decision by either side.

## Rationale
- **No contract was modified.** `ToolPort` (Core's contract) and
  `TOOL_CONTRACT`/`ToolCall` (Neptune's contract) are both left
  exactly as frozen. The adapter absorbs the mismatch entirely on its
  own side, which is exactly what an adapter is for.
- **No RuntimeDriver or ToolExecutor redesign was needed** (both
  explicitly forbidden by B-006's stop conditions) -- the gap is
  structural (a missing field in a wire-format dict), not behavioral.
- **The placeholder `turn_id` is honest, not silently wrong**: it's
  named `-pending-turn` specifically so a future reader inspecting a
  persisted `ToolResult` understands its `turn_id` was not supplied by
  Core, rather than assuming it correlates with a real `Turn` record.

## Consequences
- If a future task needs Neptune-side `ToolResult`s to correlate with
  Core's actual `Turn.turn_id` (e.g. for cross-referencing observation
  records against Core's turn history), `ToolPort.execute()`'s
  signature will need to carry that -- a genuine, if small, contract
  change on Core's side, not something this adapter can paper over
  further.
- `ToolPortAdapter` is now the canonical integration seam between the
  two lanes for tool execution. Any future tool infrastructure Claude
  B builds (beyond `echo`) is already reachable from Core Runtime
  through this same adapter without further wiring.
- This task also surfaced (and fixed, not via this ADR but directly in
  the B-006 merge commit) an unrelated cross-branch defect: both
  lanes had independently claimed ADR number 037 for different
  decisions. That is a process finding about the two-agent
  methodology's ADR-numbering coordination, not an architectural one,
  and is recorded in `DEVELOPMENT_STATE/decisions.yaml` (B-DEC-017)
  rather than as a separate ADR.

## Validation
This decision should be revisited if/when Core Runtime's `ToolPort`
contract is intentionally extended to pass richer call context (which
would be a Core-side ADR, not this one), or if a future task needs
genuine `turn_id` correlation between the two lanes' persisted
records.

## Renumbering note
Originally filed as ADR-040. Renamed to ADR-042 during the C-002
repository correction sprint, because Claude A had independently
claimed ADR-040 (plan-executor-policy.md, A-007) before the branches
were reconciled. Resolved by renumbering Claude B's ADR rather than
Claude A's, to avoid touching content Claude A's own in-progress work
may already reference. No content changed besides the number and this
note.
