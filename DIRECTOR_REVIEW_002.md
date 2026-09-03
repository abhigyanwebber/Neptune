# DIRECTOR_REVIEW_002

**Audit ID:** NEPTUNE-DIRECTOR-REVIEW-002
**Scope:** Full integrated-system audit, `main`/`worker/claude-a` at commit `27dcf9b` (B-008: ModelGateway Adapter & First Real Agent Turn)
**Mode:** Read-only. No code, contracts, or architecture were modified to produce this document.
**Auditor:** Claude A (Core / Control Plane)

---

## 1. Executive Verdict

Since `DIRECTOR_REVIEW_001.md` (the prior audit), Neptune closed the single largest gap that audit identified: a real `ModelGatewayPort` implementation now exists (`ModelGatewayAdapter`, B-008), backed by the canonical registry (not the deprecated YAML one), and a real Task has been driven through real `AgentRuntime` → real Groq API → a persisted `Turn.model_response`, live-verified with an exact-match deterministic prompt. This is genuine, not aspirational — I traced the code myself rather than trusting the commit message, and it holds up: `core/runtime/engine.py` is byte-for-byte unchanged since my last audit, the adapter never imports `core.contracts.gateway` (duck-typed, matching the `ToolPortAdapter` precedent), and the capability-vocabulary bridge I built in C-006 is genuinely consumed in the resolution path, not just present in the repo.

What is **not** yet true, and matters: no single live test proves the *entire* intended chain (`REAL LLM decides to call a tool` → `real ToolExecutor via Core's ToolPort` → `Observation` → `next Turn`) end-to-end through `AgentRuntime`. Two adjacent halves are each proven live independently — a real model call through real `AgentRuntime` (with a prompt that doesn't invoke a tool), and a real model's tool-call decision through real `ToolExecutor` (bypassing `AgentRuntime` entirely, calling `ModelGatewayService` directly, the same way B-003's original smoke test did). The full loop is proven together only with fakes/mocks. Planning remains completely unwired to anything (zero consumers outside its own package, confirmed by direct import search). Permission and sandbox layers remain entirely absent — still correctly deferred, since there is still only one trivial, harmless tool in the whole system.

I also found one small, real, low-severity defect while tracing the new adapter: `ModelGatewayAdapter._translate_request()` can raise an uncaught `ValueError` for an out-of-vocabulary capability override, before the adapter's own try/except block begins — a narrow violation of ADR-045's own "never raises" invariant, untriggered by anything in the current codebase and untested. Detailed in §5/§9.

**Verdict: PROCEED WITH CORRECTIONS.**

---

## 2. End-to-End Execution Map

| Transition | Exists? | Tested? | Actually Wired? | Real or Mocked? | Persistent? | Recoverable? |
|---|---|---|---|---|---|---|
| User Goal → Goal/Planning | `core.planning.models.Goal` exists | Yes (A-007) | **No** — nothing constructs a `Goal` outside its own tests | N/A (hand-authored in tests) | Yes (if used) | Yes (if used) |
| Plan / PlanStep | `Plan`/`PlanStep`/`PlanExecutor` exist | Yes (A-007) | **No** — zero consumers outside `core/planning/`, confirmed by direct import search across `src/` | N/A (hand-authored) | Yes | Yes, proven (A-007 two-process test) |
| Capability Resolution | `CapabilityResolver` exists | Yes (A-006) | **Yes** — consumed by `CanonicalRegistryCandidateSource` (B-008) | Real | N/A (pure logic) | N/A |
| Provider + Model Resolution | `ProviderResolver` + canonical `ModelRegistry` exist | Yes (A-006, C-004) | **Yes** — `CanonicalRegistryCandidateSource.candidates_for()` is the live path's sole registry read (B-008, replacing the legacy YAML dependency C-005 identified) | Real | Yes (Postgres) | Yes, proven (A-004/A-006/C-004 recovery tests) |
| ModelGateway | `ModelGatewayAdapter` exists | Yes (23 unit tests, B-008) | **Yes** — satisfies `core.contracts.gateway.ModelGatewayPort`, constructed and passed into real `AgentRuntime` in the live test | Real | N/A (stateless adapter) | N/A directly; downstream effects are |
| → REAL LLM | `GroqAdapter` exists | Yes, live-gated | **Yes** — `test_first_real_agent_turn_reaches_real_groq_through_agent_runtime` proves it, live, through `AgentRuntime` | **Real**, live-verified this exists in the test suite; **I could not re-run it myself** (no `GROQ_API_KEY` in this environment) — see §9 | Response persisted to `Turn.model_response` | Yes (same mechanism as every other Turn) |
| Tool Call (when required) | `ToolPort`/`ToolExecutor` exist | Yes (B-004/B-005/B-006) | **Partially** — proven live at the `ModelGatewayService` level (`test_live_groq_tool_call_to_observation`, live-gated, best-effort/skips if the model doesn't call the tool this run) but that test bypasses `AgentRuntime` entirely; proven through `AgentRuntime` only with `FakeModelGateway`/mocked responses | Mocked-through-Runtime; Real-but-bypassing-Runtime | Yes when through Runtime | Yes when through Runtime (B-006) |
| Tool Execution | `ToolExecutorService`/`EchoTool` exist | Yes | **Yes** — `ToolPortAdapter` bridges into `core.contracts.tools.ToolPort`, proven with a genuine two-OS-process recovery test (B-006) | Real (EchoTool itself is trivially real, no external call) | Yes | Yes, proven |
| Observation | `ObservationMessageBuilder`/`ObservationProcessor` exist | Yes (B-005) | **Yes**, but only proven with `MockProviderAdapter` — no live test confirms a real model's *next* response correctly incorporates a real prior observation | Mocked for the "model reads observation" half; real for the "tool produces observation" half | Yes (as Turn/Event data) | Yes |
| Next Turn | `RuntimeDriver`/`AgentRuntime.run_turn()` | Yes, extensively | **Yes** | Real (driver logic); model/tool side per rows above | Yes | Yes, proven (A-005) |
| Completion | `RuntimeDriver` complete/stop logic | Yes | **Yes** | Real | Yes | Yes, proven |
| Checkpoint / Recovery | `AgentRuntime.checkpoint()`/`resume()` | Yes, extensively | **Yes** | Real | Yes | **Yes — this is the single most rigorously proven transition in the whole system.** Genuine two-OS-process tests exist for Task/Session/Turn/Event/Checkpoint (Stage 0/1), full runtime lifecycle (Stage 2), Driver stop/resume (A-005), Registry population (A-004), Resolution reproducibility (A-006), Plan steps (A-007), and real tool-execution observations (B-006). |

**Do not infer wiring from module existence — applied throughout above.** Every "Yes" in the "Actually Wired?" column is backed by a specific test file and, where claimed "real," a specific live-gated test I located and read. Every "No" or "Partially" is backed by a specific negative check (e.g., a repo-wide import search that found zero consumers).

---

## 3. Implemented vs Actually Wired Matrix

*(Same underlying facts as §2, restated as the specifically-requested matrix.)*

| Component | Implemented | Tested | Actually Wired (into the live path) | Real or Mocked | Notes |
|---|---|---|---|---|---|
| Planning | Yes | Yes | **No** | N/A | Contracts + executor complete and self-consistent; zero external consumers |
| Resolution | Yes | Yes | Yes | Real | Consumed by `CanonicalRegistryCandidateSource` (B-008) |
| Registry (canonical, Postgres) | Yes | Yes | Yes | Real | Sole registry dependency of the live path as of B-008 |
| Registry (legacy, YAML) | Yes | Yes | **No longer required**, still present | Real (was) | Not deleted; C-005's own cutover plan treats deletion as a separate future decision |
| ModelGateway | Yes | Yes | Yes | Real, live-verified in the test suite | `ModelGatewayAdapter` (B-008) |
| Provider adapter | Yes (Groq only) | Yes | Yes | Real | Single provider (ADR-033: intentional, not yet a gap) |
| Runtime | Yes | Yes | Yes | Real | Unmodified since Stage 2; zero changes in B-008 |
| Tool execution | Yes (EchoTool only) | Yes | Yes | Real (trivial tool) | Genuine recovery-proven (B-006) |
| Observation | Yes | Yes | Yes | Mocked-provider-tested; not live-tested for the "model reads it" half | — |
| Persistence | Yes | Yes | Yes | Real (Postgres) | Consistently the strongest-evidenced layer across every task |
| Recovery | Yes | Yes | Yes | Real | See §2's checkpoint row |
| Security boundaries (permission/sandbox) | **No** | N/A | N/A | N/A | Correctly deferred — one trivial tool exists system-wide |

---

## 4. Product / Vision Alignment

Checked against `01_BIBLE/01_VISION_AND_PRINCIPLES.md` and the README:

- **Reusable, project-agnostic:** Holding. Nothing in `core/` references a specific project; the one live provider integration (Groq) sits entirely behind adapters.
- **Provider-agnostic:** Now genuinely demonstrated, not just architecturally claimed — `ModelGatewayPort` has a real, live-verified implementation with zero provider-specific leakage into `src/core` (confirmed: `src/core` diff since C-006 is empty; `ModelGatewayAdapter` imports nothing from `core.*`).
- **Self-hostable:** Unchanged assessment — local Postgres via `docker-compose.yml`, no cloud dependency introduced by B-008.
- **Claude-Code-like agent environment:** Materially closer than at the last audit — a real agent turn now actually happens, not just "the pieces that would make one exist."
- **Free/cheap-first:** Holding. Groq's free tier remains the only live provider; B-008's own commit found and fixed a real free-tier model retirement (`llama-3.3-70b-versatile` → `openai/gpt-oss-120b`), which is exactly the kind of "volatile provider fact" the Bible's registry framing anticipates, handled correctly (data-only fix, no architecture change).

**Scope drift check:** None found. No new providers, no new tools, no permission/sandbox speculative build-out, no multi-agent orchestration, no MCP, no browser automation. B-008 explicitly declined to build a new routing algorithm when `ProviderResolver`'s ranking didn't match `ModelGatewayService`'s adapter availability — it reused two already-existing fallback mechanisms (`CapabilityRouter`'s fallback_chain, `ModelGatewayService`'s adapter-presence check) rather than inventing a third. This is the correct instinct and is consistent with every prior task's discipline in this project.

---

## 5. Architecture Integrity

- **Dependency direction:** Holding. `core.contracts.gateway.ModelGatewayPort`'s Protocol is unchanged; `ModelGatewayAdapter` satisfies it structurally without importing it.
- **Core/provider isolation:** Holding, verified by direct diff (`git diff 6f89298 27dcf9b -- src/core/` is empty).
- **Registry ownership:** Now genuinely singular for the live path — `CanonicalRegistryCandidateSource` is confirmed the only registry the live Groq call depends on.
- **ModelGateway boundary:** Real and tested. One precise defect found (see below).
- **Tool boundary:** Unchanged from B-006, still solid.
- **Permission/sandbox boundaries:** N/A — don't exist yet, correctly.
- **Persistence ownership:** Unchanged, still consistently correct across every task.
- **Recovery semantics:** Unchanged, still the strongest-evidenced part of the system.
- **Planning/runtime separation:** Still fully separated — confirmed zero coupling either direction.
- **Provider adapter isolation:** Holding — `GroqAdapter` stays inside `neptune.infrastructure.providers`.

**Accidental coupling found during integration — one real defect:**

`ModelGatewayAdapter._translate_request()` (`src/neptune/infrastructure/gateway/model_gateway_adapter.py`) builds a `capabilities` list via `Capability(capability_override)` when `Task.constraints["capability"]` is set, and this construction happens **before** the method's `try/except ModelGatewayError` block. If `capability_override` is a string that is a valid *canonical* capability id but has no legacy-side enum member (e.g. `"web_search"`, `"mcp"`, `"browser"`, `"terminal"`, `"memory"` — the five canonical-only capabilities documented in my own C-006 bridge's docstring), `Capability(capability_override)` raises a plain `ValueError` that is **not** a `ModelGatewayError`, is **not** caught, and propagates straight out of `send()` — the exact failure mode ADR-045 was written specifically to prevent (`run_turn()` has no try/except around `self._gateway.send(context)`, so this would leave a `Turn` stuck in `AWAITING_MODEL` permanently).

This is narrow: nothing in the current codebase ever sets `constraints["capability"]` to one of those five values, and `test_send_capability_override_via_constraints` only exercises `"tool_use"` (a value present on both sides), so the gap is real but currently dormant and untested. It also does not use `core.registry.capability_bridge.translate_capability()` (C-006) for this specific direction at all — `canonical_registry_adapter.py` does use the bridge correctly (confirmed by reading it directly), but `model_gateway_adapter.py`'s own inline capability-override handling does not, and duplicates similar logic to `canonical_registry_adapter.py`'s local `_capability_to_external()` helper without reusing it. Low severity, easy fix (wrap the construction in the existing try/except, or reuse the bridge/`_capability_to_external` helper), flagged for correction rather than treated as blocking.

---

## 6. Contract Integrity

- **Frozen contracts respected:** Yes. `core/contracts/gateway.py`'s `ModelGatewayPort` signature is byte-for-byte unchanged.
- **No competing duplicate contracts:** Confirmed. `ModelGatewayPort` (Core) and `ModelGatewayService`/`Router` (Neptune) remain distinct, non-duplicate layers — the adapter is the seam, not a second contract.
- **Adapters satisfy intended contracts:** Yes, verified by direct reading of both `ModelGatewayAdapter` and `ToolPortAdapter` — both duck-type their respective Core Protocol without importing it.
- **Provider-specific types stay out of Core:** Confirmed by the empty diff and by `test_neptune_core_provider_independence.py` (C-005) still passing.
- **Canonical registry is source of truth:** True for the live path as of B-008. The deprecated YAML registry is still present but confirmed (by reading `gateway_service.py`'s `CandidateSource` Protocol widening) no longer the thing the live call site depends on.
- **Deprecated YAML registry not required by the live path:** Confirmed directly — `CanonicalRegistryCandidateSource` is what's wired into the live test, not `ModelRegistry.load()`.

**Contract changes:** None. `gateway_service.py`'s type-hint widening (concrete `ModelRegistry` → a small `CandidateSource` Protocol) is a Neptune-internal implementation detail, not a Core contract change, and is justified — both classes already had the identical method shape, so this is a structural-typing formalization, not new behavior.

---

## 7. Real vs Placeholder Inventory

| Subsystem | Implemented | Tested | Real Integration | Placeholder/Deferred | Notes |
|---|---|---|---|---|---|
| Planning | Yes | Yes | No | Goal-to-plan generation; any Runtime wiring | Complete relative to its own scope, inert relative to the whole system |
| Resolution | Yes | Yes | Yes | Cost/latency-aware ranking (ADR-039) | Now genuinely load-bearing (B-008) |
| Registry | Yes | Yes | Yes (canonical) | Legacy YAML deletion | Canonical wins for the live path; deletion is a deliberate future decision, not an oversight |
| ModelGateway | Yes | Yes | Yes | Multi-provider fallback beyond Groq; retry/backoff policy | The real milestone this review confirms |
| Provider adapter | Yes (Groq) | Yes | Yes | Second provider (openrouter/gemini/etc. registered as data, no adapter built) | ADR-033-consistent, not a gap |
| Runtime | Yes | Yes | Yes | — | Unchanged, solid |
| Tool execution | Yes (EchoTool) | Yes | Yes | Real tools with side effects; permission/sandbox | Everything proven works for a harmless tool; untested for a dangerous one |
| Observation | Yes | Yes | Partially (mocked-provider only) | Live-model comprehension of an observation | — |
| Persistence | Yes | Yes | Yes | — | Consistently strongest layer |
| Recovery | Yes | Yes | Yes | — | Consistently strongest layer |
| Security boundaries | No | No | No | Everything | Deferred correctly, but now closer to mattering — see §10 |

---

## 8. Production Readiness Assessment

**CORE FUNCTIONALITY PROVEN:**
- Durable state, recovery-after-restart (every entity type, genuine two-process tests)
- A real, live, end-to-end agent turn through the intended architecture
- Deterministic control-plane behavior (Driver policy, resolution ranking, plan ordering)
- Provider replaceability at the architecture level (real adapter seam proven for both tools and, now, the model gateway)

**PRODUCTION HARDENING REMAINING (not proven, not claimed to be):**
- **Reliability / retries / timeouts:** `ModelGatewayError.retriable` flag exists in the normalized error shape, but nothing in `AgentRuntime`/`RuntimeDriver` currently *acts* on it — a retriable error still just completes the Turn with an error, no automatic retry exists anywhere in Core.
- **Provider failure handling beyond the single-provider case:** untested with more than one live provider; `CapabilityRouter`'s fallback_chain exists but has never been exercised with two real, live adapters.
- **Configuration/secrets:** `GROQ_API_KEY` is read from environment directly; no secrets-management layer exists (correctly out of scope for every task so far, but a real gap before any shared/production deployment).
- **Observability:** Events provide a full audit trail, but there is no metrics/tracing/alerting layer — purely a data-availability story today, not an operations one.
- **Resource constraints / concurrency:** No load testing, no concurrent-Task behavior verified, no rate-limit-aware backpressure.
- **Deployment assumptions:** Still local-Postgres-via-docker-compose only; no containerized app image, no staging/prod topology defined (Gate 8, still not built — correctly, per ADR sequencing).
- **Security boundaries:** As above — the single biggest production-readiness gap, and the one that stops being "correctly deferred" the moment a second, non-trivial tool is registered.

Passing tests is not conflated with production readiness anywhere in this assessment — the distinction above is deliberate.

---

## 9. Test Evidence

**Collection:** `pytest --collect-only`: **227 tests collected, zero errors.**

**Full suite, this session, Postgres available, no `GROQ_API_KEY` set:**
```
222 passed, 5 skipped in 44.89s (re-run: 34.82s)
```
Skips (all live-credential, all correctly attributed):
- `tests/integration/gateway/test_live_first_agent_turn.py:84`
- `tests/test_groq_live_e2e.py:32`
- `tests/test_groq_live_e2e.py:69`
- `tests/test_groq_live_e2e.py:76`
- `tests/test_tool_execution_integration.py:109`

**Live-provider tests:** I do **not** have a `GROQ_API_KEY` in this environment and did not fabricate a live run. B-008's own report claims `227 passed, 0 skipped` with a live key present — I can confirm the *no-credential* baseline (`222/5`) matches exactly what B-008 reported for that condition, which is a real, checkable consistency signal, but I have **not personally re-verified** the live-credentialed path. This should be re-confirmed by whoever has the operator-supplied key before treating the live-Groq claim as re-validated by this audit specifically (as opposed to trusted from B-008's own report).

**Postgres-dependent tests:** All ran and passed in this session (Docker was reachable this time, unlike several prior sessions in this project's history — noted only because it has been an intermittent environmental issue, not a code issue).

**Unit vs integration split:** Not separately itemized by pytest markers in this repo; the 222/227 figures are the full suite (`tests/unit/`, `tests/integration/`, and the loose `tests/*.py` files from Claude B's earlier tasks).

---

## 10. Remaining Critical Gaps

**CRITICAL:** None. Nothing found in this audit blocks correct operation of what currently exists or represents a broken/violated contract.

**HIGH:**
1. **No permission/sandbox layer**, and the system is now materially closer to needing one — a real ModelGateway means real model output could plausibly request a real tool with real side effects sooner than before. Still correctly deferred (only `EchoTool` exists), but the "correctly deferred" window is narrowing.
2. **The full live loop (real model → real tool call → real observation → next real Turn, all through `AgentRuntime`) has never been proven in one test.** Two adjacent halves are each proven live independently, as detailed in §2. This is the most concrete, specific gap in "is Neptune actually a working agent," not just "are the pieces individually real."

**MEDIUM:**
3. `ModelGatewayAdapter`'s uncaught-`ValueError` edge case (§5) — real, currently dormant, easy fix.
4. No retry/backoff policy anywhere in Core despite the error contract already carrying a `retriable` flag — the data exists, nothing consumes it yet.
5. Legacy YAML registry (`ModelRegistry`, `config/registries/*.yaml`) still present, still functional, adding a small but real maintenance-duplication cost (two places a provider/model fact could technically be edited, even though only one is live) until the deletion decision C-005 deferred is actually made.

**LOW:**
6. `ADR-045`'s own `Status:` field still reads `PROPOSED` despite being fully implemented and tested — a minor process/paperwork inconsistency, not a functional issue.
7. `ModelGatewayAdapter`'s local capability-override handling duplicates logic already written once in `canonical_registry_adapter.py`'s `_capability_to_external()` helper rather than reusing it (related to gap #3 above — fixing #3 by reuse would also resolve this).

I am deliberately not listing a longer wishlist — per this task's own instruction, only meaningful gaps are ranked above.

---

## 11. Single Recommended Next Milestone

**Prove the full live loop in one test: a real model, given a prompt that requires it, decides to call a tool; the real `ToolExecutor` (via `ToolPortAdapter`/`core.contracts.tools.ToolPort`) executes it; the observation is fed back; the model produces a final response — all driven through real `AgentRuntime`/`RuntimeDriver`, not `ModelGatewayService` called directly.**

This is the single highest-value next step because it is the one remaining piece standing between "Neptune has proven every individual link of the intended chain" (true today, per §2) and "Neptune has proven the chain is actually a chain" (not yet true). Concretely, this likely means: extend or write a sibling to `test_live_first_agent_turn.py` that uses a prompt requiring `EchoTool` (similar to `test_live_groq_tool_call_to_observation`'s prompt) but constructs the same real `AgentRuntime`/`RuntimeDriver` wiring `test_live_first_agent_turn.py` already established, rather than calling `ModelGatewayService.infer()` directly. Given both halves already exist and are independently proven, this is very likely a test-composition task, not new production code — a small, high-confidence next step that directly closes the most concrete gap this audit found.

**Alternatives that should wait, and why:**
- **Permission/sandbox layer:** Still correctly deferred per every prior audit's reasoning — building it before a second, real tool exists means designing against a hypothetical, not evidence. The moment a second tool with real side effects is proposed, this jumps to the top of the list; it isn't there yet.
- **Second provider:** ADR-033 explicitly defers this until the single-provider loop is fully proven — and per this audit, it still isn't (the full-loop gap above). Adding a second provider now would mean testing multi-provider fallback logic before the single-provider case is completely closed.
- **Retry/backoff policy:** The `retriable` flag already exists in the error contract; building the policy that consumes it is real, valuable work, but is naturally sequenced *after* proving the full loop works at all, so retry policy has a real failure mode to be designed against rather than a hypothetical one.
- **Legacy registry deletion:** Zero urgency — it's dormant, not actively harmful, and C-005's own audit already produced a cutover plan whenever someone decides to execute it.
- **Deployment/containerization:** Still premature — there still isn't yet a fully-proven live loop to containerize (see the recommended milestone).

---

## 12. Parallel-Work / Process Assessment

The A/B ownership split (Core/control-plane vs. Infrastructure/integration) continues to function well at the *implementation* level — B-008 made zero changes to `src/core/`, confirmed by direct diff, and consistently used the adapter-seam pattern rather than reaching into Core code. This discipline has held across every task on both lanes since the project began.

**Where it has repeatedly broken down: ADR numbering.** This is now the fourth+ time this exact class of collision has occurred (documented across B-006, C-002, the pre-C-005 041 collision, and the merge-resolution task I performed most recently). The pattern is consistent and well-understood (parallel branches independently claim the same next-free number before syncing), and every occurrence has been resolved the same correct way — but the fact that it keeps recurring, even after `00_ADR_INDEX.md` was specifically built to prevent it, suggests the index alone is not sufficient. **A shared ADR-number reservation mechanism is now warranted** — the simplest version would be a single shared file (or even a one-line convention: "claim your next number by adding a placeholder title to the index in the same commit you start drafting the ADR, before writing the content") that both lanes check *before* branching, not just when merging.

**Synchronization points that are now clearly required, based on evidence from this and the prior review:** any task that touches the registry/capability vocabulary boundary (C-001 through C-006 all needed this, and needed each other's completed work to avoid redundant or conflicting decisions) should be sequenced, not parallelized, until the vocabulary/schema is genuinely stable — which, per this audit, it now is. Model Gateway work (B-008) correctly waited for C-004/C-006 to land first; this sequencing worked and should be the template going forward for any future cross-lane boundary work.

**Which work categories should have a single owner:** ADR numbering/index maintenance itself (not the ADRs' content, just the numbering ledger) — a single, small, low-risk category where dual ownership has produced repeated, avoidable friction with no compensating benefit (neither lane's work is faster for having its own independent numbering).

I am not recommending a methodology redesign — the underlying two-lane, adapter-seam approach has produced a real, working, tested system, which is strong evidence it's working. The one concrete process fix warranted by evidence is the ADR-numbering reservation point above.

---

## 13. Final Verdict

**PROCEED WITH CORRECTIONS**

The system has crossed a genuine threshold since the last audit: it can now execute a real agent turn against a real model through the architecture that was designed for it, not just contain the individually-tested pieces that would eventually make one possible. Nothing found in this audit is architecturally broken, and the one code-level defect found (§5) is narrow, dormant, and cheap to fix. The corrections warranted are: (1) close the full-live-loop test gap identified as the single recommended milestone, (2) fix the `ModelGatewayAdapter` capability-override edge case, and (3) establish the lightweight ADR-numbering reservation point recommended in §12. None of these require rework of existing, working code — all three are additive, matching this project's consistent pattern of shipping the simplest correct thing first and hardening deliberately rather than speculatively.
