# DIRECTOR_REVIEW_001

**Audit ID:** DIRECTOR-AUDIT-001
**Scope:** Full architectural audit after A-003–A-007, B-003–B-006, and the merge of `worker/claude-b` into `worker/claude-a` (commit `42b3cd1`)
**Auditor:** Claude A (Core / Control Plane)
**Nature of this document:** Audit only. No code, contracts, or ADRs were created or modified to produce it.

---

## 1. Executive Summary

Neptune's Core lane (A-003–A-007) and Infrastructure lane (B-003–B-006) are each internally coherent, well-tested, and individually faithful to the frozen Bible. The merge is clean at the source-code level — the two lanes occupy genuinely non-overlapping package roots (`src/core|application|infrastructure|config` vs `src/neptune/*`) and there are zero import-level conflicts. Recovery is proven end-to-end for every durable object Neptune currently has: Task, Session, Turn, Event, Checkpoint, Registry entries, Resolution results, Plans, and — as of B-006 — real tool-execution observations, all survive a genuine OS process restart with test evidence, not simulation.

However, the two lanes were developed for most of their history without integrating with each other, and this shows in three concrete, currently-reproducible defects: **two ADR files share the number 039 and two share the number 040** (different content, `05_DECISIONS/00_ADR_INDEX.md` lists only one side's entries); **two independent, incompatible "provider registry" systems exist** (Claude A's Postgres-backed, audited, recoverable `ProviderRegistry`, and Claude B's YAML-file-based, in-memory, non-recoverable `ModelRegistry`), with **two different, only-partially-overlapping capability vocabularies**; and **`requirements.txt` does not list `requests`**, which B's code imports directly, so three of B's own test modules fail to even collect on a fresh environment set up by following the repository's own documented setup.

None of these are architectural violations in the sense of breaking a frozen contract or dependency-direction rule — they are integration debt from genuinely parallel development, and B's own decision log (B-DEC-017) already flags the root cause. But they are real defects sitting in the repository today, not just process observations, and they should be corrected before the next milestone rather than accumulating further.

The single largest capability gap is not a defect but an absence: **`core.contracts.gateway.ModelGatewayPort` has no real implementation anywhere in the repository.** It is satisfied only by `FakeModelGateway` (`core/runtime/fakes.py`). B's real, live-validated Groq-backed Model Gateway stack (`neptune.core.contracts.model_gateway`, `router`, `provider_adapter`) has never been wired to it — unlike the Tool boundary, which B-006 bridged cleanly via `ToolPortAdapter`. This is the one missing link standing between the current state and a genuine, fully-persisted, fully-recoverable, live end-to-end agent turn — exactly the "first vertical slice" the Bible's own README describes.

**Verdict: PROCEED WITH CORRECTIONS.**

---

## 2. Architecture Assessment

### 2.1 Contracts

All of Claude A's contracts (`core/contracts/*.py`) remain pure Protocols with zero infrastructure or provider imports, enforced by an automated test (`tests/contract/test_core_provider_independence.py`) that has passed unmodified through every A task since Stage 0/1. Claude B's `neptune/core/contracts/*.py` also appears provider-independent on manual inspection (no `requests`/`litellm`/`sqlalchemy` imports found anywhere under `src/neptune/core`), but **there is no automated test enforcing this for B's tree** — the existing contract test only scans `src/core`. This is an easy, low-risk gap to close (extend the existing test or add a parallel one) and is noted in the Risk Register rather than treated as a live violation, since manual inspection found no actual breach.

Frozen contracts (`03_CONTRACTS/*.md`) have not been edited by either lane. Two tasks (B-004, B-012 in the decision log) explicitly frame their work as "implementing the frozen contract, not modifying it" (`core/contracts/tool_execution.py` giving `TOOL_CONTRACT.md` concrete shape) — consistent with the Bible's authority order.

### 2.2 Boundaries

The Task/Agent/Session/Turn/Event/Checkpoint boundary (Claude A) and the Model Gateway/Router/Provider Adapter/Tool Executor boundary (Claude B) are architecturally distinct and, on the evidence, correctly so — this mirrors the Bible's own separation of control-plane orchestration from provider-facing execution. The one boundary crossing that has actually been built, `ToolPortAdapter` (`src/neptune/infrastructure/tools/tool_port_adapter.py`), is a genuinely clean piece of work: it satisfies `core.contracts.tools.ToolPort` structurally (duck-typed, no inheritance, matching how Neptune's own adapters satisfy its Protocols), imports nothing from `core.*`, and absorbs an attribution mismatch (`ToolCall` needs `task_id`/`session_id`/`turn_id`; `ToolPort.execute()` is deliberately opaque) entirely on Neptune's own side without touching either contract. This is exactly the seam pattern the architecture calls for, and it is the strongest single piece of evidence that the two-lane boundary design works when actually exercised.

The equivalent seam for the Model Gateway does not exist (see §1 and §5).

### 2.3 Dependency Direction

`02_ARCHITECTURE/02_DEPENDENCY_DIRECTION.md`'s core rule — core/domain never imports infrastructure or provider SDKs — holds for Claude A's tree, mechanically enforced. It appears to hold for Claude B's tree by inspection (provider SDKs/`requests` are confined to `neptune/infrastructure/providers/`). No cross-tree dependency violation was found in either direction: `src/core` does not import `src/neptune`, and `src/neptune` does not import `src/core` except through the one legitimate seam (`ToolPortAdapter` importing `neptune.core.contracts.tool_execution`, which is B's own contract, not Claude A's — it satisfies Claude A's `ToolPort` structurally, without importing it).

### 2.4 Persistence Model

Single-database, single-ORM-base persistence remains true only for Claude A's tree. Every table Claude A introduced (tasks, agents, sessions, turns, events, checkpoints, capabilities, providers, resources, tool_definitions, plans) lives under one SQLAlchemy `Base` (`infrastructure/persistence/models/base.py`) and one Postgres instance (`docker-compose.yml`). **Claude B's entire stack has zero persistence of its own** — no SQLAlchemy import, no Postgres reference, anywhere under `src/neptune`. This is not itself wrong (a stateless Model Gateway/Tool Executor is defensible under ADR-009's "state is infrastructure-owned" principle — execution services are not supposed to own state), but it does mean B-006's recovery proof works entirely because `ToolPortAdapter` is stateless and Claude A's `AgentRuntime` supplies all the durability. If a future Model Gateway bridge is built the same way (stateless adapter, Core owns the state), the persistence model stays unified. If it is built any other way, this becomes a real risk.

Two independent registry *data* sources now exist: `06_REGISTRIES/data/*.yaml` (Claude A, loaded into Postgres via `registry_loader.py`, feeding `ProviderRegistry`) and `config/registries/*.yaml` (Claude B, loaded directly into memory via `ModelRegistry.load()`, feeding the Router). See §5.

### 2.5 Runtime Model

`AgentRuntime` (`core/runtime/engine.py`) and `RuntimeDriver` (`core/runtime/driver.py`) are unmodified by any B task — confirmed by direct instruction compliance in B-005 and B-006 ("Do NOT modify RuntimeDriver... Do NOT modify Runtime" was honored) and by inspection. The hybrid loop (ADR-016: planning + iterative execution + verification + checkpointing + events) is expressed correctly: every lifecycle step emits an Event, and the driver's continue/complete/stop decision (ADR-038) is a plain, deterministic function of the last Turn's `tool_calls`. B-006 extended this proof with a **real** tool call (not `FakeToolPort`) and it held without any Runtime/Driver change — the strongest evidence available that the runtime model's provider-independence claim is real, not aspirational.

### 2.6 Planning Model

`PlanExecutor` (A-007) is fully isolated from both the Runtime/Driver and from B's stack — no cross-references exist in either direction. This is architecturally clean but also means the planning layer is not yet load-bearing: nothing in the repository currently constructs a `Plan` from a real goal, and nothing currently drives a `Turn` from a `PlanStep`. This is correctly scoped as out-of-bounds for A-007 (explicitly excluded: "Do not build sophisticated reasoning... Do not build research logic"), but it means the Planning layer is a contract-and-executor shell today, not yet a working part of the agent loop.

### 2.7 Tool Execution Model

Concrete and load-bearing. `ToolExecutor` (B-004) normalizes every failure mode into a `ToolResult` rather than raising (B-DEC-013), directly implementing `TOOL_CONTRACT.md`'s invariant that tool existence/lookup failure is not fatal to the caller. `EchoTool` is deliberately trivial (no side effects, no sandbox need) — correct scope for a reference tool proving the boundary, not a production tool. No permission/authorization check exists anywhere in the tool-execution path (B-DEC-014 explicitly documents this as a known, deferred gap, matching `PERMISSION_CONTRACT.md`'s status as a frozen-but-unimplemented contract). No sandbox exists either (`SANDBOX_CONTRACT.md`: same status).

### 2.8 Recovery Model

This is the architecture's strongest area by far. Every durable object type has a genuine two-OS-process recovery test (not a same-process simulation): Task/Session/Turn/Event/Checkpoint (Stage 0/1), the full runtime lifecycle (Stage 2), the Driver's stop/resume boundary (A-005), Registry population (A-004), Resolution reproducibility (A-006), Plan step execution (A-007), and now real tool-execution observations (B-006). This consistency across seven independently-built recovery tests, all following the same "kill the process, start a new one, prove state was never in memory" pattern, is a genuine architectural asset — it's difficult to accidentally break durability with this much test coverage of the actual failure mode the Bible cares about (Gate 2, Gate 9).

---

## 3. Vision Alignment Assessment

Cross-referencing `01_BIBLE/01_VISION_AND_PRINCIPLES.md` (there is no standalone `VISION.md` file in the repository — vision is expressed there and in the README; this audit treats `01_VISION_AND_PRINCIPLES.md` as authoritative for this purpose and flags the missing filename as a minor documentation-discoverability gap only):

- **Provider-agnostic agent OS (O1):** Holding, with one caveat. `core.contracts.gateway.ModelGatewayPort` genuinely has no provider-specific code depending on it, and the one real provider integration that exists (Groq) sits entirely behind Claude B's own `ProviderAdapter` Protocol, not hard-coded into anything Core-facing. The caveat: because no adapter bridges B's Gateway into Core's Protocol yet, provider-agnosticism is currently proven only within B's own stack, not proven for the actual `AgentRuntime` that's supposed to be the provider-agnostic control plane. The claim is architecturally intact but empirically unverified at the point that matters most.
- **Capability-driven (architecture remains):** Partially drifting. Two independent capability vocabularies now exist with only partial overlap (`core.registry.capability_registry.KNOWN_CAPABILITIES`: reasoning, coding, web_search, vision, tool_use, mcp, browser, terminal, memory, planning; `neptune.core.domain.capability.Capability`: fast_general, coding, reasoning, planning, summarization, classification, tool_use, vision, embedding, frontier_escalation). Five values overlap by name; five exist only on each side. Nothing currently breaks because of this (the two systems don't yet talk to each other), but it means "capability-driven" is currently true twice, in two incompatible ways, rather than once.
- **Contract-first:** Holding strongly. Every task on both lanes points to a specific frozen contract it's implementing (TASK_CONTRACT, SESSION_CONTRACT, TOOL_CONTRACT, PROVIDER_CONTRACT, ROUTER_CONTRACT, etc.), and no task modified a frozen contract to make its own job easier.
- **Persistence-first:** Holding for Claude A's tree; not yet applicable to Claude B's (see §2.4) — B's services are correctly stateless, with Claude A's infrastructure carrying persistence for the one boundary that's integrated (tools). Not a violation, but worth watching as more of B's stack gets bridged in.
- **Resumable:** Holding, strongly evidenced (§2.8).
- **Multi-provider:** Not yet demonstrated. Exactly one real provider (Groq) has been integrated end-to-end. Gate 10 ("remove the first provider adapter and configure a second candidate; core/application code unchanged") has not been attempted. ADR-033 explicitly defers this ("one provider before multi-provider resilience"), so this is on-plan, not drift.
- **Deterministic where intended:** Holding. `RuntimeDriver`'s continue/complete/stop policy, `PlanExecutor`'s step selection, and `ProviderResolver`'s ranking are all explicitly, testedly deterministic (ADR-038, ADR-039/A-006, ADR-040/A-007's ordering sections). No hidden nondeterminism was found.

**Flagged drift:** the dual-registry/dual-vocabulary situation (§2.4, §5) is the one place where "one architecture, replaceable resources" is currently expressed as two parallel, non-communicating implementations of the same idea. This is drift worth correcting, not a vision failure — the underlying principle (capability-driven routing over hard-coded providers) is respected on both sides individually.

---

## 4. Layer-by-Layer Assessment

### Registry Layer
- **Complete:** CRUD, verification metadata, YAML import/export, audit trail via existing Event infrastructure, dependency resolution with cycle detection, a verified five-provider seed dataset (Groq/OpenRouter/Gemini/Ollama/openai_compatible) with real, checked documentation sources.
- **Partially complete:** Only the fixed A-003 vocabulary (plus A-004's two additions) is populated; `openai`/`cerebras`/`mistral` remain unregistered.
- **Intentionally deferred:** Router logic itself (this layer only exposes lookups a Router should use).
- **Assumption surfaced by this audit:** that this would be *the* provider registry Neptune uses. In practice, Claude B's Router uses its own separate YAML-based registry instead (§5), so this assumption currently does not hold in practice for the one subsystem (routing) that would consume it most naturally.

### Resolution Layer
- **Complete:** Capability lookup, provider ranking (status → verification_status → alphabetical), dependency expansion, graceful no-match handling, full reproducibility proof across a process restart.
- **Partially complete:** Ranking has no cost/latency/quota signal (explicitly deferred to ADR-039, pending live operational data).
- **Intentionally deferred:** Everything Router-specific — this layer is consumed by, not a replacement for, a future Router.
- **Assumption:** that a future Router would be built on top of this layer's `ProviderResolver`. Claude B already built a Router (`neptune.infrastructure.routing.capability_router`) independently, before this layer existed, and it does not consume `ProviderResolver` — it queries B's own `ModelRegistry` directly. This assumption is currently false in practice.

### Runtime Layer
- **Complete:** Full lifecycle (Task→Agent Run→Session→Turn→Checkpoint→Resume→Complete), Model Gateway/Tool boundary Protocols, driver-level continue/complete/stop policy, checkpoint-and-resume proven at both the runtime and driver level, and — as of B-006 — with a real tool in the loop.
- **Partially complete:** Only ever driven by `FakeModelGateway` for the model side; never by a real provider through the actual `ModelGatewayPort` boundary.
- **Intentionally deferred:** Loop-continuation policy beyond "did this turn call a tool" (ADR-038's Validation section, explicitly waiting on a real Gateway's response shape).
- **Hidden assumption worth surfacing:** that closing the Model Gateway gap will be a small adapter, analogous to `ToolPortAdapter`. This is plausible given how clean that precedent is, but unverified — B's `ModelGatewayService.infer()` raises exceptions on failure rather than returning a result type (B-DEC-002), which is a different error-handling convention than `ModelGatewayPort.send()` currently assumes (a plain dict return, with `RuntimeDriver` reading `tool_calls` off it). The adapter will need to translate that, not just wire the two together.

### Tool Layer
- **Complete:** Definition/lookup/execution/normalization boundary (B-004), one reference tool (echo), full recovery proof through Core's runtime (B-006).
- **Partially complete:** Only one trivial tool exists; nothing exercises a tool with real side effects, real risk, or a real sandbox requirement.
- **Intentionally deferred:** Permission/authorization (B-DEC-014, explicit), sandboxing (SANDBOX_CONTRACT.md status).
- **Assumption:** that `ToolExecutor.execute()` is safe to call unconditionally. It currently is, only because nothing dangerous has been registered as a tool yet. This assumption will not survive a second, real tool with side effects — permission/sandbox work needs to land before that happens, not after.

### Observation Layer
- **Complete:** Deterministic single-message observation format (ADR-039/B-005, `role="tool"` ContextMessage, sorted-key JSON for success / structured failure string for failure), a two-turn mock-provider scenario proving the model actually sees and responds to the observation.
- **Partially complete:** Only validated against `MockProviderAdapter`, not against a real model's actual behavior when shown that format (B-003's live Groq call predates B-005 and didn't exercise the observation format).
- **Intentionally deferred:** Multi-tool-call-per-turn observation batching, observation truncation/bounding (Gate 7 territory).

### Planning Layer
- **Complete:** Full contract (Goal/Plan/PlanStep/StepStatus), executor (start/select/start-step/complete/fail-with-cascade/skip/is_complete), deterministic ordering, dependency-graph validation reusing A-003's resolver, full recovery proof.
- **Partially complete:** Nothing — this layer is complete relative to its own explicit scope.
- **Intentionally deferred:** Goal-to-plan generation (no AI-authored plans exist; every test plan is hand-constructed), any wiring between a `PlanStep` and an actual `Turn`/tool call.
- **Assumption:** none currently exercised, since nothing consumes this layer yet. It is the newest, least load-bearing piece of the architecture.

---

## 5. Risk Register

| # | Risk | Evidence | Severity |
|---|---|---|---|
| 1 | **Duplicate ADR numbers.** `05_DECISIONS/ADR-039-resolution-layer-selection-policy.md` (A) and `ADR-039-observation-feedback-format.md` (B) both exist; same for `ADR-040-plan-executor-policy.md` (A) and `ADR-040-toolport-attribution-seam.md` (B). `00_ADR_INDEX.md` lists only B's ADR-039/040, not A's — the index itself is now inaccurate. | Confirmed by direct file listing. | Medium — no functional impact yet, but any future reference to "ADR-039" or "ADR-040" is ambiguous, and the index (the mechanism meant to prevent exactly this) is stale. |
| 2 | **Two incompatible provider/model registries.** Claude A's Postgres-backed, audited `ProviderRegistry` (A-003/A-004) vs. Claude B's YAML-file, in-memory `ModelRegistry` (B-001, predates A-003). Neither is aware of the other; B's Router queries only its own. | `config/registries/*.yaml` vs `06_REGISTRIES/data/*.yaml`; zero cross-references found. | High — this is the largest concrete duplication in the repository and the direct cause of risk #3. |
| 3 | **Two incompatible capability vocabularies.** `core.registry.capability_registry.KNOWN_CAPABILITIES` vs `neptune.core.domain.capability.Capability` — 5 of 10 values differ on each side. | Direct file comparison, §3. | Medium — silent mismatch risk once/if these two systems are ever asked to interoperate (e.g. a `PlanStep.capability_id` meant to inform B's routing). |
| 4 | **Missing dependency in `requirements.txt`.** `requests` is imported directly by `neptune/infrastructure/providers/groq_adapter.py` but never added to `requirements.txt`; 3 of B's test modules fail to collect on a clean environment following the documented setup. | Reproduced directly: `ModuleNotFoundError: No module named 'requests'` on `pytest --collect-only` before manual install. | Medium — easy fix, but currently breaks the documented "clone and `pip install -r requirements.txt`" path for a fresh contributor. |
| 5 | **No real Model Gateway integration.** `ModelGatewayPort` has exactly one implementation in the whole repository (`FakeModelGateway`). | `grep`-level search for `def send(self, request` found only `core/contracts/gateway.py` (the Protocol) and `core/runtime/fakes.py`. | High — this is the single biggest capability gap; see §6. |
| 6 | **No permission or sandbox layer.** Confirmed absent by B-DEC-014 and by `SANDBOX_CONTRACT.md`/`PERMISSION_CONTRACT.md` both being frozen-but-unimplemented. | Direct code inspection; no matching module exists anywhere. | Medium today (only a trivial, harmless tool exists), **will become High the moment any tool with real side effects is registered.** |
| 7 | **No automated provider-independence check for Claude B's core.** The existing test only scans `src/core`. | `tests/contract/test_core_provider_independence.py`, `CORE_DIR = .../src/core`. | Low today (manual inspection found no violation), but unenforced. |
| 8 | **Cross-branch integration cadence.** `worker/claude-a` and `worker/claude-b` were developed for the majority of this project's history without being merged into each other, discovered only when B-006 required both lanes to run in the same process. Already self-flagged in B-DEC-017 ("flagging for director review of the two-agent methodology's cross-branch integration cadence"). | Commit log + B-DEC-017's own note. | Medium — process risk, not a code defect; the fact it was self-caught and self-flagged is a positive signal, but it's the root cause of risks 1–3. |
| 9 | **Bible Phase 1 Acceptance Gates: partial coverage.** Mapping current state against `12_VALIDATION/09_PHASE_1_ACCEPTANCE_GATES.md`: Gate 1 (mostly met), Gate 2 (met), Gate 3 (met only within B's isolated stack, not through Core's boundary — see risk 5), Gate 4 (not met — no permission engine, no sandbox), Gate 5 (partially met — process-death recovery proven extensively, but induced provider-timeout/rejection/malformed-output scenarios are not yet tested end-to-end through the real stack), Gate 6 (not built), Gate 7 (not built), Gate 8 (not built), Gate 9 (met, strongly), Gate 10 (not attempted). | Direct comparison against the gate document. | Informational — most un-met gates are correctly out of scope for tasks completed so far, not slippage. Flagged for roadmap context (§6). |
| 10 | **Scaling/migration risk: schema evolution has no migration tool.** `create_all()` doesn't alter existing tables; this has already required manual `docker compose down -v` resets at least three times across A-004/A-005/A-006 work (per Claude A's own decision log, e.g. ADR-A-010's known_limitation note). Flagged previously as `NEPTUNE-DIRECTOR-ALEMBIC-DECISION`, still unresolved. | `DEVELOPMENT_STATE/dependencies.yaml`. | Low today (local dev only), **will become Medium-High once a shared/staging database exists** that can't simply be dropped. |

---

## 6. Recommended Next Milestone

**Bridge the Model Gateway boundary: build the adapter that lets `AgentRuntime`/`RuntimeDriver` drive Claude B's real, live-validated Model Gateway stack through `core.contracts.gateway.ModelGatewayPort`, using the same pattern `ToolPortAdapter` already proved for tools.**

This is the single most logical next brick, for four convergent reasons:

1. **It is the one missing piece of an otherwise-complete chain.** The Bible's own README describes the first vertical slice as `Task → Session → Context → Model Gateway → Router → LiteLLM → one free model → one safe tool → Event → Checkpoint → Verification`. Every link in that chain exists today and has been individually proven — except the Model Gateway link is not actually wired into the chain; it's proven only in isolation (B's own scripts bypass `AgentRuntime` entirely, per B-DEC-008). Building this bridge doesn't create new capability so much as it *connects capability that already exists*, which is the highest-leverage kind of next step available.
2. **A working precedent already exists and de-risks the work.** `ToolPortAdapter` is a template: bind a stateless adapter to task/session identity at construction time, satisfy Core's opaque-dict Protocol, translate Core's minimal error convention (`status: "error"`) to/from Neptune's own richer result types. The only genuinely new problem to solve is B-DEC-002's exception-raising convention (`ModelGatewayService.infer()` raises rather than returning a result), which the adapter needs to catch and translate into `ModelGatewayPort.send()`'s plain-dict-return convention.
3. **It resolves the audit's highest-severity risk (§5, risk 5) directly**, and does so without needing to first resolve the registry duplication (risk 2/3) — the Gateway bridge only needs the *provider adapter and router*, not the registry data source those components currently read from. Registry unification can and should happen, but doesn't block this.
4. **It produces the first genuine, live, end-to-end, fully-persisted, fully-recoverable agent turn** — Task created, real model called through the real boundary, real tool executed if requested, real observation fed back, real checkpoint, real resume — which is the actual proof-of-concept the entire two-lane effort has been building toward. Nothing else on the roadmap produces a comparably concrete, demonstrable milestone.

**Sequencing note (not a rejection, a recommendation for how to open this milestone):** before or alongside starting the adapter, do the small, mechanical corrections from risk 1 and 4 (rename one side's ADR-039/040, fix the index; add `requests` to `requirements.txt`). These are minutes of work each, block nothing architecturally, but will otherwise sit as small paper cuts through the next milestone too.

---

## 7. Milestones Explicitly Rejected For Now

- **Permission/Sandbox layer (Gate 4).** Genuinely important, but there is currently exactly one tool in the entire repository and it has no side effects (`EchoTool`). Building an authorization/sandbox layer with nothing risky to protect against would mean designing it speculatively rather than against a real second tool's actual needs — the same reasoning Claude A's own ADR-A-006 already applied to loop-continuation policy ("wait for real signal before designing further"). This should be the milestone immediately *after* either the Model Gateway bridge or a second real tool is registered, whichever comes first — not before.
- **Registry/vocabulary unification (risks 2–3).** Real debt, but lower urgency than the Gateway bridge: nothing currently breaks because of it (the two systems don't talk to each other yet), and unifying them properly requires a design decision (which registry wins? do vocabularies merge or does one map to the other?) that deserves deliberate director attention, not a rushed fix bundled into an unrelated milestone. Recommend a dedicated, focused task once the Gateway bridge reveals whether the Router actually needs Claude A's registry data at all (it may turn out B's Router's own registry is sufficient for its purposes, in which case "unification" might mean documenting the intentional separation rather than merging).
- **Economic control (Gate 6) and Context control/compaction (Gate 7).** Both require live usage data from a working end-to-end loop to design against meaningfully (token counts, actual latency, actual retry patterns). Building either before the Gateway bridge exists means designing against assumptions instead of evidence — the same trap ADR-038 and ADR-A-006 both explicitly avoided elsewhere in this codebase.
- **Deployment/containerization (Gate 8).** Premature: there is not yet a complete, live, working core loop to containerize. Packaging an incomplete slice produces a deployable artifact that doesn't do the thing Neptune is for.
- **Multi-provider proof (Gate 10).** ADR-033 already explicitly defers this until after the single-provider core loop passes, and that loop still doesn't exist end-to-end (see recommended milestone). Attempting a second provider now would mean proving replaceability of a boundary that hasn't been proven to work with the first provider yet.

---

## 8. Final Verdict

**PROCEED WITH CORRECTIONS**

The architecture remains sound, the vision remains intact in principle on both lanes individually, and the recovery/persistence discipline is genuinely strong across the board. Nothing found in this audit requires rework of existing code — every defect identified is additive-fix territory (rename a file, add a line to requirements.txt, build one new adapter) rather than "undo and redo" territory. The corrections in §5 (risks 1 and 4 especially) are small and should be done promptly since they cost little and currently degrade a new contributor's or reviewer's ability to trust the repository's own index and setup instructions. The recommended milestone (§6) is the correct next step precisely because it is additive, not corrective — it connects two already-complete lanes into the first real proof of what Neptune is for.
