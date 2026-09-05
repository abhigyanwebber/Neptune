# DIRECTOR_REVIEW_003

**Audit ID:** NEPTUNE-DIRECTOR-REVIEW-003
**Scope:** Product-readiness audit, `worker/claude-a` at commit `3ce762d` (B-009: Full Live Agent Loop Integration Validation)
**Mode:** Read-only. No code, contracts, architecture, or Bible content modified to produce this document.
**Auditor:** Claude A (Core / Control Plane)

---

## Executive Verdict

The gap Review 002 identified as the single remaining piece of "is Neptune actually a working agent" — proving the full loop (real model decides to call a tool → real execution → real observation → real second turn → completion) together, in one live test, through real `AgentRuntime` — is now closed. I verified this directly rather than trusting the commit message: `tests/integration/runtime/test_full_live_agent_loop.py` makes eight explicit, evidence-mapped assertions (not inferred ones) covering every transition in the chain, `src/core/` has a byte-for-byte empty diff since my last review, and the two live defects B-009 found and fixed (`tool_choice` never set; `ModelGatewayAdapter` never populated `ModelRequest.tools` at all — the latter recorded as ADR-046, correctly, since it was a structural impossibility, not a bug) were both fixed at the adapter layer with zero Core changes.

But closing that gap changes what "the bottleneck" means. Neptune can now run one real, complete agent turn against one real, trivial, harmless tool. It **cannot yet** do anything a user would recognize as "a coding agent" — there is no file-reading tool, no shell tool, no permission layer, and (this review's most important finding) **the model cannot currently be told what tools exist at runtime**: `ModelGatewayAdapter.tool_definitions` is a fixed list supplied once at construction, because `core/runtime/context.py`'s context dict has no tool-availability concept at all (ADR-046's own stated root cause). This is not a missing tool — it's a missing *wiring point* for tools, and it sits directly in the path of the actual next bottleneck this review identifies.

**Verdict: PROCEED WITH CORRECTIONS.**

---

## Current Product Capability

**PROVEN NOW:**
- A real user-supplied requirement, driven through real `AgentRuntime`/`RuntimeDriver`, reaches a real LLM (Groq)
- That model can decide to call a real tool, have it really executed, see the real result, and produce a real final answer — in one continuous, persisted execution
- The entire loop survives a genuine process restart mid-execution (turn 1's tool call and observation persist; a new process resumes and completes turn 2)
- Every durable object type in the system (Task, Session, Turn, Event, Checkpoint, Registry entries, Plans) has independently, genuinely proven recovery
- Provider-agnosticism is proven at the architecture level (real adapter seam for both tools and the model gateway, zero Core coupling in either)

**INTENDED BUT NOT YET PRODUCT-COMPLETE:**
- Anything resembling a *useful* coding/workspace agent — there is exactly one tool (`EchoTool`), which does nothing but echo text back
- Dynamic tool availability — the model can only ever see the tools an adapter was hardcoded with at construction, not tools the system discovers or the user configures per-task
- Any permission, approval, or sandbox boundary — the Bible has a designed model for this (see §Security below); none of it is built
- Goal-to-plan generation — `PlanExecutor` exists, works, and is fully recovery-tested, but nothing in the system ever constructs a `Plan`; every plan in every test is hand-authored
- Multi-provider operation — architecturally proven possible, operationally exercised with exactly one provider (Groq), consistent with ADR-033's explicit sequencing, not yet exercised with two

I am not inflating either list: the "proven now" items are each backed by a specific test I read directly; the "not yet" items are each backed by a specific absence I verified (grep/diff showing zero consumers, zero implementation, or zero second-provider exercise).

---

## Claude-Code-Like Experience Gap Analysis

| Capability | Classification | Evidence |
|---|---|---|
| Repository/workspace interaction | NOT YET BUILT | No filesystem-scoped tool exists; `EchoTool` has no workspace concept |
| File reading/writing | NOT YET BUILT | No such tool registered anywhere |
| Shell/command execution | NOT YET BUILT | No such tool registered anywhere; `TOOL_CONTRACT.md`/`06_REGISTRIES/data/tools.yaml` list `terminal` as a *vocabulary* entry only, no implementation |
| Tool discovery | ARCHITECTURALLY READY, NOT YET BUILT | `ToolRegistry`/`CapabilityResolver` exist and can enumerate tools by capability; nothing wires that enumeration into what a model is actually offered at request time (the ADR-046 gap) |
| Tool authorization | NOT YET BUILT | No concept exists in code anywhere |
| Permissions | ARCHITECTURALLY READY, NOT YET BUILT | `07_SECURITY/02_PERMISSION_MODEL.md` defines a real 4-tier precedence model (Global/Workspace/Task deny > Explicit approval > Allow rule) and an example policy table; zero implementation (`grep` for `class.*Permission` across `src/` returns nothing) |
| Sandboxing/isolation | ARCHITECTURALLY READY, NOT YET BUILT | `SANDBOX_CONTRACT.md` is frozen but unimplemented; correctly so — nothing dangerous exists to sandbox yet |
| Planning | IMPLEMENTED BUT INCOMPLETE | Plan representation/execution is complete and tested (A-007); goal→plan generation does not exist |
| Context handling | IMPLEMENTED BUT INCOMPLETE | `assemble_context()` produces task/session/requirements/recent-events; no tool-availability, no repository/file content, no token budgeting |
| Iterative tool use | PROVEN | The two-turn live loop is exactly this, proven live |
| Error recovery | PROVEN for infra failure (process death); NOT YET BUILT for model/provider retry | Checkpoint/resume is proven repeatedly; nothing retries a `retriable` model error automatically |
| Checkpoint/resume | PROVEN | Strongest-evidenced capability in the whole system, unchanged assessment from Review 002 |
| Provider/model replacement | PROVEN architecturally, single-provider operationally | Real adapter seam for both boundaries; one live provider exercised |
| Observability | IMPLEMENTED BUT INCOMPLETE | Full Event audit trail exists; no metrics/tracing/alerting layer |
| Cost/resource control | NOT YET BUILT | No budget/quota enforcement anywhere; `ModelResult.usage` is captured and stored but nothing acts on it |
| Security boundaries | NOT YET BUILT (see above) | — |

I am not demanding anything the Bible deliberately defers — sandboxing, permissions, and cost control are all explicitly staged for later in the Bible's own gate sequence (`12_VALIDATION/09_PHASE_1_ACCEPTANCE_GATES.md` Gates 4 and 6), and this table reflects that, not a generic checklist.

---

## Security / Permissions Assessment

**Current security boundary:** None, functionally. `ToolExecutorService` will execute any tool it has registered, unconditionally, for whatever arguments the model supplies — there is no interception point between "model requested this" and "this ran."

**What `ToolExecutor` can currently do:** Exactly what `EchoTool` does — accept a text string and echo it back. No filesystem access, no network access, no process spawning exist anywhere in the current tool surface, so the *practical* current risk is genuinely near-zero — but that is a fact about what tools happen to exist, not a fact about any enforced boundary.

**What permission enforcement exists:** None. Confirmed by direct search (`class.*Permission`, `class.*Sandbox` across all of `src/`: zero matches, unchanged since Review 002).

**What sandbox/isolation exists:** None.

**What is intentionally deferred:** Everything above — and correctly so as of *this* commit, per the Bible's own gating (`PERMISSION_CONTRACT.md`/`SANDBOX_CONTRACT.md` are frozen contracts specifying the shape, deliberately left unimplemented pending real tools to protect against; `07_SECURITY/02_PERMISSION_MODEL.md`'s own example policy table is explicitly marked "initial policy examples, not final production policy").

**Should security be the next milestone?** Not yet, and not because it doesn't matter — because building it now would mean designing against zero real risk surface (one harmless echo tool) rather than the actual tools it will eventually need to govern (a shell tool's "run tests: allow, install package: ask" distinction from the Bible's own example table only makes sense once a shell tool exists to apply it to). This is the same reasoning every prior audit in this project has applied to this exact question, and the evidence hasn't changed the answer — but see §Single Biggest Product Bottleneck below for why this is now closer to being the *right* next answer than it was at Review 002.

---

## Tool Surface Assessment

The current system proves exactly one tool: `EchoTool`, a no-side-effect, no-external-dependency reference implementation whose entire purpose (per B-004's own decisions) was proving the `ToolPort` boundary, not being useful.

Per `04_RESEARCH/01_HARNESS_REPORT_NOTES.md` (already surveyed in ADR-037's evaluation, not re-litigated here): mature coding-agent harnesses converge on a small, consistent core tool surface — file read/write/edit, shell execution, and search/grep, with everything else (browser, MCP) layered on top as optional. Neptune's own `06_REGISTRIES/data/tools.yaml` already reflects this exact shape as *vocabulary* (`browser`, `terminal`, `filesystem`, `search`, `mcp` — five entries, zero implementations).

**Minimum real tool surface required before Neptune is meaningfully useful for coding/workspace tasks, per this evidence:** a filesystem tool (read/write/edit within a scoped workspace) and a shell/terminal tool (run a command, capture output) — the two the research corpus and Neptune's own registry vocabulary both already identify as foundational, and the two a permission model's example policy (§Security) is written to assume exist. Browser and MCP are correctly excluded from "minimum" — they're both already classified as optional/deferred by the same research this project already did (ADR-037: Cline/Roo mode-based permissions and Goose's MCP-native orientation were both classified "C — reference" or "D — not reused" for exactly this kind of near-term work).

I am not implementing or designing these tools here — this section answers "how far" and "what's minimum," per the task's own instruction, using research conclusions already reached rather than reopening the research program.

---

## Planning / Goal Decomposition Assessment

**What Planning can do:** Represent an ordered set of steps with dependencies, select the next executable step deterministically, handle failure with cascading skip, detect completion, and survive a process restart mid-execution — all genuinely proven (A-007's test suite, unchanged and unreferenced by any subsequent task).

**What Planning cannot do:** Produce a `Plan` from anything. There is no code path anywhere in the repository that takes a natural-language goal and emits `PlanStep` objects — confirmed by direct search: zero consumers of `core.planning` outside its own package, unchanged since Review 002 and B-009 touched nothing in this area.

**Is goal-to-plan generation now a major bottleneck?** Not yet, and for a specific reason worth being precise about: goal-to-plan generation is itself a job for a real model call through the now-proven `ModelGateway` path — it isn't blocked by anything architectural, it's simply a feature nobody has built yet, and building it *before* there's a real tool surface for the resulting plan steps to act on would produce plans with nothing to execute against. The tool-surface gap is upstream of the planning gap in terms of what unlocks product value first.

---

## Context / State Assessment

**What exists today:** `assemble_context()` (`core/runtime/context.py`) builds `{task_id, session_id, agent_id, task_status, requirements, constraints, recent_events[-10:]}`. Task/Session/Turn/Event/Checkpoint state is fully durable and recoverable — the strongest-evidenced part of the entire system, unchanged assessment across all three reviews.

**What's missing, and which of it materially limits usefulness today (not a wishlist):**
1. **Tool availability is not a context concept at all** — this is the concrete finding ADR-046 surfaced and fixed only at the adapter layer (a hardcoded list at construction), not at the Core level. This is the most material gap: it means the *set of tools a model can be offered* cannot currently vary per-task, per-session, or by any registry lookup at request time — it's frozen at adapter-construction time. This directly blocks "tool discovery" (§Gap Analysis) from ever becoming real, regardless of how many tools eventually get built.
2. **No repository/workspace content in context** — directly downstream of "no filesystem tool exists yet" (§Tool Surface); not a separate gap to fix independently.
3. **No token/size budgeting on `recent_events`** — a fixed last-10 slice, fine for today's trivial scale, a real limitation the moment turns carry large tool outputs (e.g. file contents, once a filesystem tool exists).

I am naming only the minimum that materially limits usefulness, per the task's instruction — #1 is the one that actually blocks something (dynamic tool offering) rather than just being incomplete in a way nothing yet depends on.

---

## Production Hardening Assessment

Using evidence from code/tests/ADRs only, consistent with Review 002's findings (B-009 did not touch this area except where noted):

- **Retries/backoff:** Still none. `ModelError.retriable` exists in the normalized error shape (unchanged); nothing in `RuntimeDriver`/`AgentRuntime` consumes it.
- **Timeouts:** `GroqAdapter` makes a synchronous HTTP call; no explicit timeout configuration was found in the code I read (worth a direct follow-up check by whoever owns that file next, since I did not exhaustively re-audit every provider-adapter internal this session).
- **Rate limits:** Provider-published quota is recorded as *data* (`06_REGISTRIES/data/models.yaml`'s `quota_snapshot` field, C-004) but nothing enforces or backs off against it.
- **Provider failover:** `CapabilityRouter`'s fallback_chain mechanism exists but has never been exercised with two real, live adapters (unchanged from Review 002).
- **Malformed responses:** `ModelGatewayAdapter._error_response()` normalizes failures into a structured dict rather than raising — genuinely solid, proven by the live test's own turn-1/turn-2 clean-response assertions.
- **Concurrency:** No concurrent-Task behavior has been tested anywhere in this project's history.
- **Configuration/secrets:** `GROQ_API_KEY` read directly from environment; B-009's own commit message explicitly confirms operator-supplied, in-memory-only, never persisted/logged — good discipline, but still no secrets-management layer exists.
- **Observability:** Event audit trail only, as noted above.
- **Deployment:** Still local-Postgres-via-docker-compose only; no container image, no staging/prod topology (Gate 8, still correctly not built).
- **Resource limits:** None enforced.
- **Deterministic behavior:** Strong where it matters — `RuntimeDriver`'s policy, `ProviderResolver`'s ranking, `PlanExecutor`'s step ordering are all deterministic and tested as such. The live model's own tool-calling decision is, correctly, the one deliberately non-deterministic part of the system (it's supposed to be), and B-009's test acknowledges this honestly (a failure message distinguishing "real-model variance" from "architectural failure" rather than papering over it).
- **Failure recovery:** Proven extensively for process death; not proven at all for provider-side failure (a live 5xx or malformed response mid-loop has never been deliberately induced and observed end-to-end).

None of this is new relative to Review 002 except where explicitly marked — B-009 was correctly scoped to the live-loop proof, not hardening.

---

## Free / Cheap-First Feasibility

Holding. Groq remains the only live, wired provider — still $0 (free tier), still the only one ADR-033 says should exist right now. `06_REGISTRIES/data/providers.yaml` has four other providers registered as *data* (OpenRouter, Gemini, Ollama, openai_compatible) with real, verified endpoint/pricing facts (C-004), none of them wired to an adapter — this is exactly the intended sequencing, not drift. No paid provider has become foundational anywhere — I checked specifically for this and found no code path that assumes or requires a paid tier. Local model option (Ollama) is registered as data with `depends_on: [local_fs]` but, like the others, has no adapter — architecturally ready, not operationally exercised. I am not redoing the provider research; nothing in this session's evidence contradicts the existing research corpus's conclusions.

---

## Single Biggest Product Bottleneck

**Minimum coding tool surface — specifically, the combination of (a) no real tools beyond `EchoTool` and (b) no mechanism for the model to be told what tools exist except a hardcoded list at adapter construction (ADR-046's finding).**

I am choosing this over the other candidate categories deliberately:
- **Permissions/sandboxing** is a close second, but per the reasoning in §Security, it cannot be meaningfully designed until there's a real tool surface with real risk to govern — it is *downstream* of the tool-surface gap, not parallel to it.
- **Goal-to-plan generation** is real but not yet load-bearing — per §Planning, building it now would produce plans with nothing real for their steps to act on, since the only real tool is `EchoTool`.
- **Context/repository awareness** is real but is itself mostly a *consequence* of not having a filesystem tool yet (§Context, item 2) rather than an independent blocker.
- **Production hardening** matters for a shared/production deployment, but Neptune isn't yet at the stage where hardening a system that can only echo text has product value — hardening what exists today would be effort spent polishing a proof-of-concept, not unlocking usefulness.
- **Multi-turn control policy** (`RuntimeDriver`'s policy) is already proven live and working — not a bottleneck at all right now.

Every other candidate is either downstream of this one or premature relative to it. This is not a giant wishlist — it is the one item that, left unaddressed, keeps every other candidate blocked or speculative.

---

## Single Recommended Next Milestone

**Name:** Minimum Real Tool Surface + Dynamic Tool Offering

**Objective:** Build a small, real, useful tool surface (filesystem read/write/edit and shell/terminal execution, per §Tool Surface's minimum finding) registered through the existing `ToolRegistry`/`ToolExecutor`/`ToolPort` boundary already proven in B-004/B-006/B-009, **and** close the ADR-046 gap by making the set of tools offered to the model derive from a registry lookup (e.g. `CapabilityResolver`/`ToolRegistry` at request time) rather than a fixed list at adapter construction.

**Why now:** It is the evidence-identified single bottleneck (above), it builds directly on infrastructure already proven twice (`ToolPort`/`ToolExecutor` for execution, `ModelGatewayAdapter.tool_definitions` for offering — just needs to become dynamic instead of static), and it is the prerequisite every other deferred category (§What Must Wait) is actually waiting on, not a parallel nice-to-have.

**Prerequisites:** None architecturally new — `ToolRegistry`, `ToolExecutor`, `ToolPort`, `ModelGatewayPort`, and the canonical registry are all already real, tested, and live-verified. This milestone is additive integration work on proven foundations, matching this project's consistent pattern (every successful milestone so far has been exactly this shape).

**What it unlocks:** A genuinely useful (if still unpoliced) coding-workspace agent for the first time; a real risk surface that makes designing the permission/sandbox layer possible with actual requirements instead of speculation; a real destination for goal-to-plan generation's output.

**What should explicitly wait:** permissions/sandboxing (needs this milestone's real tools to design against); goal-to-plan generation (needs this milestone's real tools to act on); multi-provider exercise (ADR-033, unaffected by this milestone either way); production hardening beyond what's already solid (needs a system worth hardening for real use first).

**What the other worker lane (B) should do, if anything:** Nothing speculative in parallel. If the director authorizes this milestone, the natural split (consistent with every prior successful sequencing in this project) is: Claude A owns any Core-side context/contract implications if the dynamic-tool-offering mechanism turns out to need one (uncertain until designed — ADR-046 itself notes Core's context dict *could* eventually need a native tool-availability concept, but doesn't require it), and Claude B owns the actual tool implementations and the adapter-side wiring, exactly the same ownership split that made B-004/B-006/B-009 work. I am not assigning speculative parallel work to B beyond this — the task instruction is explicit that I should not start speculative parallel work, and I'm treating "assign B something to do in parallel right now" as exactly that unless the milestone itself is authorized first.

---

## What Must Wait

- Permissions/sandboxing (needs real tools to govern)
- Goal-to-plan generation (needs real tools to act on)
- Multi-provider exercise (ADR-033-sequenced, unaffected by the recommended milestone)
- Cost/resource control (needs real usage patterns from real tool use to design against)
- Deployment/containerization (still nothing production-shaped to deploy yet)
- Retry/backoff policy (has a real `retriable` flag to design against already, but is lower leverage than the tool-surface gap right now — nothing currently retries because nothing currently needs to, at this system's current usage scale)

---

## Two-Worker Process Recommendation

The A/B split continues to function well at the implementation level — B-009, like every task since the split began, made zero changes to `src/core/` (confirmed by diff), used the established adapter-seam pattern for both fixes, and correctly escalated the tool-definitions gap to a genuine ADR rather than quietly working around it. This is strong, repeated evidence the boundary is right, not something to redesign.

**ADR reservation is now mandatory, not merely recommended.** Review 002 already flagged this as warranted; the recurrence count (4+ collisions across this project's history, all resolved the same correct way, all avoidable with a one-line reservation convention) is sufficient evidence on its own, and nothing in this review found a reason to soften that recommendation. I am treating this as confirmed rather than re-litigating it.

**Which work belongs on which lane, going forward, based on the recommended milestone:** tool implementations (filesystem, shell) and their `ToolPort` bindings belong on B's lane — direct continuation of B-004/B-006's ownership. Any Core-side context/contract change (only if the dynamic-tool-offering design turns out to need one) belongs on A's lane — direct continuation of how every Core contract in this project has been owned. **What must be single-owner:** the capability/registry vocabulary (already established by C-001 through C-006 — this review found no new reason to revisit that), and now explicitly the ADR numbering ledger (above). **What can safely run in parallel:** implementation work within each lane's already-established ownership, exactly as it has been running.

**Synchronization points required for the recommended milestone specifically:** if the dynamic-tool-offering mechanism needs any Core-side change, that change should land and be reviewed *before* B's tool implementations are wired to depend on it — the same sequencing discipline that made C-004/C-006 → B-008 → B-009 work cleanly (each waited for its dependency to land rather than parallelizing against an assumption).

I am not proposing a methodology redesign — the evidence supports the existing structure with the one already-flagged correction (ADR reservation) now confirmed necessary rather than merely suggested.

---

## Test Evidence

**Collection:** `pytest --collect-only`: **230 tests collected, zero errors** (up from 227 at Review 002 — the 3 new B-009 test files).

**Full suite, this session, Postgres available, no `GROQ_API_KEY` set:**
```
224 passed, 6 skipped in 41.03s
```
Skips (all live-credential, all correctly attributed — verified with `-rs`):
- `tests/integration/gateway/test_live_first_agent_turn.py:84`
- `tests/integration/runtime/test_full_live_agent_loop.py:86` — **the B-009 milestone test itself**
- `tests/test_groq_live_e2e.py:32`, `:69`, `:76`
- `tests/test_tool_execution_integration.py:109`

This exactly matches B-009's own reported no-credential baseline (224/6), which is a real, checkable consistency signal.

**Unit tests:** Included in the above; not separately marker-partitioned in this repo (unchanged from Review 002's note on the same point).

**Integration tests:** Included in the above; all Postgres-dependent integration tests ran and passed this session (Docker was reachable).

**Postgres-dependent tests:** All passed, none skipped for Postgres-unavailability this session.

**Live-provider tests:** All 6 live-gated tests skipped in this session because **I do not have a `GROQ_API_KEY` in this environment**. I did not fabricate a live run. B-009's own report claims `230 passed, 0 skipped` with a live key present, including two consecutive full-loop test passes against the real Groq API. I have **not personally re-verified** that claim — the no-credential baseline matching exactly is meaningful corroborating evidence, but is not the same as independently re-running the live test myself. This should be understood as "consistent with, not independently re-confirmed by, this specific audit session."

**Full-loop tests:** `test_full_live_agent_loop.py` (live, skipped this session, see above), `test_full_agent_loop_mock.py` (deterministic, ran and passed — real `AgentRuntime`/`RuntimeDriver`/`ToolPortAdapter`/`ToolExecutorService`/`EchoTool`/Postgres, only the model faked via the existing `FakeModelGateway`), `test_full_agent_loop_recovery.py` (genuine two-OS-process recovery extension of the full loop, ran and passed).

---

## Final Verdict

**PROCEED WITH CORRECTIONS**

Neptune has crossed a second genuine threshold since Review 001: it is no longer just "architecturally sound" (Review 001) or "individually real, not yet proven together" (Review 002) — the full intended agent loop now genuinely runs, live, against a real model, with real (if trivial) tool execution, and survives a real process death mid-execution. That is the correct bar for "PROCEED," not "REWORK REQUIRED." The "WITH CORRECTIONS" qualifier reflects that Neptune is still a proof-of-concept relative to the stated product goal — one real tool, no permission boundary, no dynamic tool offering — and the single recommended milestone above is the evidence-identified, correctly-sequenced next step to close that gap, not a sign anything built so far is wrong. Nothing in this audit found broken architecture, a violated contract, or scope drift; every finding is either "proven and solid" or "correctly not yet built," with one precisely-located gap (dynamic tool offering, ADR-046) identified as the thing actually worth building next.
