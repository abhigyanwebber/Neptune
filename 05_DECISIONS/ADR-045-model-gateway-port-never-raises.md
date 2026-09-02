# ADR-045 — ModelGatewayPort Never Raises (B-008 Finding)

**Status:** PROPOSED

## Context
B-008 required building `ModelGatewayAdapter`, satisfying Claude A's
`core.contracts.gateway.ModelGatewayPort.send(request: dict) -> dict`.

`core/contracts/tools.py`'s `ToolPort.execute()` explicitly documents
that it must never raise -- failures are represented as data. `core/
contracts/gateway.py`'s `ModelGatewayPort.send()` docstring does not
make the same promise explicitly. Critically, `core/runtime/engine.py`'s
`run_turn()` calls `response = self._gateway.send(context)` with **no
try/except around it** -- unlike ToolPort calls, which the engine does
wrap defensively. If `send()` raises, the exception propagates straight
out of `run_turn()`, leaving the just-updated `Turn` row stuck in
`AWAITING_MODEL` status (already persisted before the call) rather than
reaching `COMPLETED` or any other terminal state.

## Decision
`ModelGatewayAdapter.send()` never raises. On any Gateway/Router/
Provider failure (`ModelGatewayError`), it catches the exception
internally and returns a plain dict carrying a normalized `error` key
(`error_type`, `message`, `retriable`, `provider_id`) instead --
`content: None`, `tool_calls: []`. Core stores this as ordinary opaque
`turn.model_response` data (it doesn't interpret dict shape beyond
`.get("tool_calls")`), and the Turn reaches `COMPLETED` normally, with
the failure preserved and inspectable in persisted state.

This adopts `ToolPort.execute()`'s already-established convention
(B-006/ADR-044) for `ModelGatewayPort.send()` too, even though
`ModelGatewayPort`'s own docstring doesn't spell it out -- inferred
from Core's actual call-site behavior (no try/except), which is the
more reliable signal of the contract's real requirement.

## Rationale
- **No contract was modified.** `ModelGatewayPort`'s signature
  (`dict -> dict`) is unchanged; this decision only fixes what
  `ModelGatewayAdapter` does internally on the failure path.
- **Consistent with the existing precedent.** `ToolPortAdapter`
  already established this exact pattern for the tool-execution seam;
  applying the same convention to the model-gateway seam keeps the two
  Core-facing adapters behaviorally consistent, rather than one
  "never raises" and the other "sometimes crashes the Runtime."
- **Checked whether the existing contract already supported this**
  (per B-008's "Architectural Discipline" instruction): `ModelResult`/
  `ModelError`/`ModelGatewayError` (B-001) already carry everything
  needed to build a normalized error dict -- no new Neptune-side type
  was required, only a translation step in the adapter.
- **Not a mere implementation detail**: this determines whether a
  provider outage or bad request leaves a Task permanently stuck in
  `AWAITING_MODEL` (silent hang, no error surfaced anywhere Core would
  notice) or completes cleanly with the failure visible in persisted
  state -- a real behavioral/architectural choice, which is why this
  is recorded as an ADR rather than left as an inline comment.

## Consequences
- Any future `ModelGatewayPort` implementation (a second provider
  adapter, a multi-provider gateway, etc.) should follow the same
  never-raise convention, or Core's un-wrapped call site becomes a
  reliability hazard again for that implementation specifically.
- If Core's own `engine.py` is ever revisited to add a try/except
  around `self._gateway.send(context)` (matching how it already
  treats `ToolPort.execute()` calls, if it does), this adapter-level
  workaround would become redundant defense-in-depth rather than the
  sole safeguard -- still correct to keep, not required to remove.
- Callers inspecting `turn.model_response` must check for the
  `"error"` key before trusting `"content"`/`"tool_calls"` -- this is
  the same discipline `FakeToolPort`'s `{"status": "error", ...}`
  convention already requires of `ToolPort` callers.

## Validation
Revisit if Core's `ModelGatewayPort` contract is ever formally amended
to document its own error-handling convention explicitly (making this
ADR's inference unnecessary), or if `engine.py` adds exception handling
around the gateway call site that changes what's actually required.
