# DIRECTOR_REVIEW_004

**Audit ID:** NEPTUNE-DIRECTOR-REVIEW-004
**Scope:** RuntimeDriver per-turn context plumbing seam discovered during B-011
**Mode:** Read-only architecture/contract review. No code, contracts, or Bible content modified.
**Auditor:** Claude A (Core / Control Plane)

---

## Branch-State Discrepancy (reported, not guessed)

The task specifies verifying `worker/claude-a` contains B-011. **It does not.**

- `worker/claude-a` = `1b03f00` (contains B-009, A-008, B-010, Review 003)
- `main` = `4e25c94` (B-011) = `worker/claude-a` + exactly one commit
- `git log main..worker/claude-a` is **empty** — nothing has diverged; `main` is a clean fast-forward ahead

B-011 exists only on `main` and `origin/worker/claude-b`. Per the instruction not to guess and not to reset/rewrite history, I did **not** merge. I audited B-011's content read-only from `main` (via `git show main:<path>`) and ran the suite on both branches separately. Every finding below was confirmed against the actual files.

This is a bookkeeping gap, not a conflict — `git merge main` (or `git pull --ff-only`) on `worker/claude-a` would fast-forward cleanly with zero conflicts.

---

## Executive Verdict

The seam is **real, correctly diagnosed by B-011, and narrower than it first appears.** It is not a missing abstraction — it is a missing *pass-through* of an abstraction `AgentRuntime` already exposes correctly.

`AgentRuntime.run_turn(session_id, extra_context=None)` has accepted and correctly merged per-turn context since Stage 2 (`engine.py:147`, `:173-175`). `RuntimeDriver._run_loop()` calls `self._runtime.run_turn(session_id)` (`driver.py:148`) — positionally, with no `extra_context` at all. Nothing in Core drops or filters the value; the driver simply never offers one.

So the direct answer to the task's own sharpest question ("Is RuntimeDriver simply failing to pass through an abstraction already correctly exposed by AgentRuntime?") is: **yes, exactly that.** This is an API-completeness gap in one Core class, not an architectural flaw, and not a contract problem.

**Verdict: PROCEED WITH CORRECTIONS** (corrections detailed in Final Verdict — they are the branch state above and an ADR-number decision, neither of which is a code defect).

---

## Current Runtime Call Chain

### A. Convenience path (today)

```
RuntimeDriver.execute_task(task_id, role, requirements, constraints, project_id)
  → AgentRuntime.create_task / start_agent_run / start_session
  → RuntimeDriver._run_loop(task_id, session_id, agent_id, turns_already_run)
      → AgentRuntime.run_turn(session_id)          # driver.py:148 — no extra_context
          → assemble_context(task, session, recent_events)   # engine.py:173
          → if extra_context: context = {**context, **extra_context}   # engine.py:174-175 (never reached)
          → ModelGatewayPort.send(context)
      → AgentRuntime.checkpoint(...)
      → policy: tool_failed / should_complete / should_continue
```

`execute_until_stop()` reaches the identical `_run_loop`, so both public entry points share the gap.

### B. B-011's direct composition path (what actually worked)

B-011 bypassed `RuntimeDriver`'s loop entirely and rebuilt it in test code:

```
resolver.available_tools(capability_ids=["tool_use"])        # real ToolOfferingResolver (A-008)
  → AgentRuntime.run_turn(session_id, extra_context={"available_tools": offerings})
      → context merged (engine.py:174-175)  ✓
      → ModelGatewayAdapter._translate_request() reads request["available_tools"]  ✓
  → RuntimeDriver.tool_failed / should_complete / should_continue   # reused unchanged, as static methods
```

B-011's own test module docstring states this explicitly, and its helper is literally named `_run_loop_with_extra_context(...)` — a duplicate of `RuntimeDriver._run_loop()`'s policy, written because the real one could not carry the context. B used only existing public API and modified neither `RuntimeDriver` nor `AgentRuntime` (confirmed: `git diff` shows no `core/` changes in `4e25c94`).

---

## Dynamic Context Flow

| Stage | Mechanism | Status |
|---|---|---|
| Tool discovery | `ToolOfferingResolver.available_tools()` queries canonical `ToolRegistry` fresh per call (A-008) | Works |
| Context injection | `run_turn(..., extra_context=...)` merges into the context dict | Works |
| Gateway consumption | `ModelGatewayAdapter._translate_request()` prefers `request["available_tools"]` over its static constructor list (A-008), expanded to concrete schema'd definitions (B-011) | Works |
| **Driver loop** | `_run_loop()` → `run_turn(session_id)` | **Drops it — never supplied** |
| Persistence | merged context stored as `turn.model_request` (`engine.py`) | Works |

Every link works except the driver's.

---

## Exact Seam Identified

**One line:** `src/core/runtime/driver.py:148`

```python
turn = self._runtime.run_turn(session_id)
```

**Is the loss intentional policy or an API limitation?** An API limitation. I checked for evidence of deliberate exclusion and found none: ADR-038 (the driver's own policy ADR, which I authored in A-005) discusses continue/complete/stop, `max_turns`, checkpoint cadence, and tool-failure handling — it says nothing about withholding context, because at A-005 no per-turn context concept was in use by anything. `extra_context` was added to `run_turn` in Stage 2 and remained unexercised until A-008 created the first real producer of per-turn context. The driver was written before there was anything to pass.

Confirming this is not merely test convenience: `extra_context` lives on `AgentRuntime` (Core production code), is merged into the context that becomes `turn.model_request` (persisted, audit-visible), and is consumed by the production `ModelGatewayAdapter`. It is part of the intended runtime model.

---

## Candidate Designs

### Option A — `extra_context` parameter on the driver's public methods
`execute_task(..., extra_context=...)` / `execute_until_stop(..., extra_context=...)` → threaded through `_run_loop` → `run_turn`.

- Additive, backward compatible, trivially understood.
- **Weakness:** one dict is captured before the loop and reused for every turn. That is a *snapshot*, not request-time discovery — it partially defeats A-008's deliberate no-caching design, and a tool registered mid-task would not appear. B-011's own sketch flagged this ("harder to use correctly across a multi-turn loop where offerings might need to change turn to turn").
- Requires touching 3 signatures (`execute_task`, `execute_until_stop`, `_run_loop`).

### Option B — RuntimeDriver constructs tool context itself
Driver imports/constructs `ToolOfferingResolver` and builds `available_tools` internally.

- **Rejected.** Directly couples `core.runtime` to `core.resolution` and to tool-discovery concerns. It would make the driver — whose entire documented purpose (ADR-038, ADR-A-006) is *loop policy only* — responsible for knowing what tools are. It also hard-codes one kind of context, blocking future per-turn context (permissions, workspace policy) from using the same channel without further redesign.

### Option C — Context-provider callable supplied at construction
`RuntimeDriver(runtime, config, context_provider=...)`, where `context_provider` is a plain callable invoked once per turn.

- Preserves per-turn freshness: the resolver is re-queried each turn, exactly as A-008 designed.
- Zero coupling: Core sees only `Callable[[str], dict[str, Any]]`. It imports nothing from `core.resolution`, nothing provider-specific. The caller wires the resolver.
- Generalizes to future per-turn context (permissions, workspace policy, resource constraints) through the same channel with no further API change.
- Touches 2 places (`__init__`, `_run_loop`) — **fewer than Option A**.
- "Premature?" — I weighed this seriously against this project's consistent ship-the-simplest-thing precedent. It is not premature, because the minimal form is a single optional parameter and one line in the loop; no Protocol class, no new module, no framework. It is smaller than Option A while being more correct.

### Option D — Keep the current API; compose externally (status quo)
Accept B-011's pattern as the supported way.

- **Rejected for the product.** It requires every real consumer to re-implement `_run_loop`'s policy (checkpoint cadence, `tool_failed`/`should_complete`/`should_continue`, `max_turns`, outcome mapping) to get dynamic tools. B-011 did exactly that in test code and said so plainly. That duplicated policy will drift from the real one. Shipping a "convenience path" that cannot carry the one thing a coding agent needs means the convenience path is not the product path — which contradicts Review 003's stated requirement that tool discovery flow through Neptune's *normal* runtime path.

No additional alternatives are proposed — none are supported by repository evidence.

---

## Compatibility / Persistence Impact

Assessed for the recommended design (Option C, minimal form):

- **Existing callers:** Every caller of `execute_task`/`execute_until_stop` in the repository is a test (verified by repo-wide search; the only non-test references are inside `driver.py` itself). With `context_provider=None` as default, `run_turn(session_id, extra_context=None)` is invoked, and `engine.py`'s `if extra_context:` makes `None` a no-op — **byte-identical behavior to today.**
- **AgentRuntime:** unchanged. It already does the right thing.
- **Recovery:** unaffected. `extra_context` is not itself persisted as separate state; the merged context is stored in `turn.model_request`. On resume, a driver constructed with the same provider recomputes offerings fresh — which is *more* correct than replaying a stale snapshot would be.
- **Checkpoints:** unaffected — checkpoint payload is task status + last turn id/sequence (`engine.py`), untouched by this change.
- **Multi-turn execution:** improved — this is the case Option A handles poorly and C handles correctly.
- **Fake/test runtimes:** `FakeModelGateway`/`FakeToolPort` need no change; the existing 7 driver unit tests and both driver recovery tests construct `RuntimeDriver(runtime)` or `RuntimeDriver(runtime, config=...)` positionally/by keyword and are unaffected by a new trailing optional parameter.
- **Public contracts:** none modified. `ModelGatewayPort`, `ToolPort`, and every frozen `03_CONTRACTS/` document are untouched.
- **Provider independence:** preserved. The callable returns a plain dict; no provider SDK type, no `neptune.*` import, enters `core/`. Both existing provider-independence contract tests continue to apply unchanged.

The smallest change is fully additive and backward-compatible.

---

## Product Relevance

**This is a true product blocker — narrowly scoped.**

Tying it to the stated requirement ("a real coding/workspace agent must discover the tools available for the current request and pass those definitions to the LLM through Neptune's normal runtime path"): today, the *only* way to get dynamic tools to a model is to not use `RuntimeDriver`. Since `RuntimeDriver` is the documented convenience/product path for driving a task to completion, the product path and the capable path are currently disjoint.

It is not a *deep* blocker — nothing is architecturally wrong, no contract is violated, and B-011 proved the full live chain genuinely works. It is a one-line-plus-one-parameter completeness gap sitting directly on the product's critical path. That combination (high product impact, minimal correct fix) is what makes it worth doing next rather than later.

---

## Security / Future Compatibility

Not designing these systems here — only checking the recommended seam doesn't foreclose them:

- **Permissions / tool authorization:** per-turn by nature (what a model may call can depend on the turn, the task, prior observations). A per-turn context channel is the natural carrier. Option C accommodates this with no further API change; Option A's per-call snapshot would need replacing.
- **Workspace policy / sandboxing:** likewise per-turn or per-session; same channel.
- **Resource constraints:** budget/quota state that changes turn to turn would use the same mechanism.
- **Important boundary to preserve:** a context provider supplies *offerings* (what exists), never *authorization* (what is permitted). `TOOL_CONTRACT.md`'s invariant — "tool existence does not grant permission" — must continue to hold; the eventual permission layer belongs between tool request and execution (`ToolPort`/`ToolExecutor` side), not in the offering channel. The recommended design does not blur this, because the provider only produces context the model *sees*; it grants nothing.

---

## Single Recommended Design

**Option C, minimal form: one optional constructor parameter, one line changed in `_run_loop`.**

Exact change (illustrative — implementation is a separate, unauthorized task):

```python
# core/runtime/driver.py — __init__
def __init__(
    self,
    runtime: AgentRuntime,
    config: Optional[DriverConfig] = None,
    context_provider: Optional[Callable[[str], dict[str, Any]]] = None,
) -> None:
    ...
    self._context_provider = context_provider

# core/runtime/driver.py — _run_loop, replacing line 148
extra_context = self._context_provider(session_id) if self._context_provider else None
turn = self._runtime.run_turn(session_id, extra_context=extra_context)
```

Caller wiring (outside Core, unchanged components):
```python
driver = RuntimeDriver(
    runtime,
    context_provider=lambda _session_id: {"available_tools": resolver.available_tools(capability_ids=["tool_use"])},
)
```

**Why this is the minimum correct change:**
1. It passes through an abstraction `AgentRuntime` already exposes correctly — adding no new concept to Core's runtime model.
2. It touches fewer signatures than Option A (2 vs 3) while correctly preserving A-008's request-time freshness.
3. It introduces zero coupling: Core gains a callable type, not a dependency on `core.resolution`, tools, or any provider.
4. It is fully additive — default `None` reproduces today's behavior exactly.
5. It generalizes to the per-turn context that permissions/workspace policy will need, without committing to any of their design now.

**Why alternatives wait:** Option B is architecturally wrong (couples policy to discovery). Option A is weaker *and* larger for the same goal. Option D leaves the product path unable to do the product's core job and guarantees duplicated loop policy.

**What must remain untouched:** `core/runtime/engine.py` (already correct — the temptation to "also tidy" it should be resisted), `ToolOfferingResolver`, `ModelGatewayAdapter`, `ToolPort`/`ToolExecutor`, the canonical registry, planning, and all frozen contracts. The fix is confined to `driver.py` plus its tests.

---

## Next Implementation Task

**Proposed:** `A-009 — RuntimeDriver Per-Turn Context Provider`

- **Owner: Claude A.** `src/core/runtime/driver.py` is Core / control-plane — A's lane by the established split, and this is a change to a Core public class. Claude B should not own it; B's lane correctly stopped at reporting the finding (B-DEC-031), which was the right call.
- **Scope:** the two edits above, plus focused tests (default-`None` back-compat; provider called once per turn; provider result reaches `turn.model_request`; a composition test replacing B-011's duplicated `_run_loop_with_extra_context` helper with the real driver).
- **Natural follow-on (not part of it):** once this lands, B-011's mock composition test can be simplified to use the real `RuntimeDriver`, and its live dynamic-tools test can run through the real convenience path — which would make the product path and the proven path finally the same path.

---

## Test Evidence

Both runs below were executed this session against a real Postgres. No live-provider results are claimed — I have no `GROQ_API_KEY` in this environment.

**`worker/claude-a` @ `1b03f00`:** collected 293 → **287 passed, 6 skipped**, 0 failed
**`main` @ `4e25c94` (includes B-011):** collected 303 → **296 passed, 7 skipped**, 0 failed

`main`'s 296/7 matches B-011's own reported no-credential baseline exactly — useful corroboration.

Exact skip reasons (all live-credential, none masking a failure):
- `tests/integration/gateway/test_live_first_agent_turn.py:84` — GROQ_API_KEY not set
- `tests/integration/runtime/test_full_live_agent_loop.py:86` — GROQ_API_KEY not set
- `tests/integration/runtime/test_full_live_agent_loop_dynamic_tools.py:117` — GROQ_API_KEY not set (`main` only; B-011's live gate)
- `tests/test_groq_live_e2e.py:32`, `:69`, `:76` — GROQ_API_KEY not set
- `tests/test_tool_execution_integration.py:109` — GROQ_API_KEY not set

Specifically inspected: B-011's dynamic-offering tests (`test_full_agent_loop_dynamic_tools_mock.py`, `test_dynamic_offering_expansion.py`, `test_full_live_agent_loop_dynamic_tools.py`), `tests/unit/runtime/test_driver.py` (7 tests), `tests/unit/runtime/test_engine.py`, `tests/unit/gateway/test_dynamic_tool_offering_integration.py` (A-008), and the driver/runtime/tool-execution recovery tests.

**Environment note for the director:** Postgres-dependent tests initially skipped because an unrelated project's container (`ai-arena-db`) holds host port 5433, so `neptune-postgres` started with no published port (`docker ps` showed bare `5432/tcp`). I did not touch the other project's running database. I ran Neptune's own container on port 5434 against its existing volume (`neptune-a_neptune_pg_data`) to obtain the real numbers above, then removed that temporary container. `docker-compose.yml` was **not** modified. If both projects need to run concurrently, Neptune's host port will need changing.

---

## ADR / Process Notes

No ADR file created; no number self-assigned, per this task's rule and Review 003's confirmed-mandatory reservation policy.

**Proposed decision, for director sign-off** (B-011 proposed the same thing under a slightly different title in B-DEC-031; I'm consolidating rather than duplicating):

> **Title:** "RuntimeDriver per-turn context supplementation via an injected context provider"
> **Substance:** `RuntimeDriver` accepts an optional per-turn context-provider callable at construction and invokes it once per turn, passing the result to `AgentRuntime.run_turn(..., extra_context=...)`. Core gains a callable type only — no dependency on tool discovery, resolution, or any provider.

**Is an ADR actually warranted?** Honest assessment, both ways: *for* — it adds a public extension point to a Core class and establishes the channel future per-turn concerns (permissions, workspace policy) will use, which is the kind of precedent ADRs exist to record. *Against* — it is pass-through plumbing of an abstraction `AgentRuntime` already exposes, which is closer to the implementation-detail category that ADR-A-014/A-015/A-016 handled as `DEVELOPMENT_STATE` decision records. I lean slightly toward **yes, assign a number**, because of the future-channel precedent rather than the code size. The director should decide; implementation should not begin until that call is made.

---

## Final Verdict

**PROCEED WITH CORRECTIONS**

**On the specific question — is RuntimeDriver context plumbing architecturally ready to implement?** Yes, unambiguously. The receiving abstraction already exists and is correct; the contract shape is settled; the change is additive and provably backward-compatible (every existing caller is a test, and `None` reproduces current behavior exactly); provider independence and all frozen contracts are unaffected; and the design generalizes to the per-turn concerns already on the roadmap without committing to them now. There is no unresolved architectural question blocking implementation.

**The two corrections are not code defects:**
1. **Branch state** — `worker/claude-a` is one commit behind `main` (missing B-011). A clean fast-forward resolves it; I did not merge, per the no-guessing/no-history-rewriting instruction.
2. **ADR number** — the director should decide whether the proposed decision above warrants a numbered ADR, and assign one if so, before A-009 begins.

Nothing in this review requires rework of anything already built. B-011's handling of the seam — finding it, proving the maximum real path without it, refusing to patch Core unilaterally, and reporting it with a proposed title instead of self-assigning a number — was exactly correct process, and is the reason this review had clean evidence to work from.
