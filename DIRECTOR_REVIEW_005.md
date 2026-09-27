# DIRECTOR-REVIEW-005 — Integrated Control Loop / Product Readiness Audit

**Read-only audit. No implementation code, contracts, planning,
permissions, RuntimeDriver, tools, providers, or Bible content was
modified in the production of this review.**

Target: `worker/claude-a` @ `df2b65e` (A-010 merged with B-012, no
conflicts, zero shared-bookkeeping files touched by either task).

---

## 1. Executive Verdict

Neptune does **not yet** have a coherent end-to-end control loop. It
has two independently complete, independently well-tested subsystems
that have never been wired to each other:

1. **Goal → Plan generation** (A-010): works, is validated, is
   persisted, is unit- and (honestly-pending-live) integration-tested.
2. **Plan → runtime → tool → observation → completion** (B-009/A-008/
   A-009/B-010/B-011/B-012): works, is validated, is persisted, is
   recoverable, and now has tool-boundary permission enforcement.

**No code anywhere in `src/` or `tests/` ever passes a `GoalPlanner`-
produced `Plan` into `AgentRuntime`, `RuntimeDriver`, or `PlanExecutor`
alongside a running agent turn.** A repo-wide search for any file that
imports both `PlanExecutor` and `AgentRuntime`/`RuntimeDriver` returns
only `core/planning/planner.py` and `core/planning/executor.py`
themselves, and in both cases the only occurrences are docstring
*comparisons* ("same pattern as AgentRuntime…"), not actual calls. This
is not a subtle seam — it is a complete absence of a wire between the
two halves of the product.

A second, more foundational gap makes this seam less surprising than
it first appears: **Neptream has no product entry point of any kind.**
There is no `main.py`, no CLI, no API surface, no script under
`src/` — nothing a user (human or otherwise) can invoke. Every
"proven" capability, including B-009's full live agent loop and
B-011's real coding-agent composition, is proven exclusively inside
test files that hand-construct the entire dependency graph
(registries, resolvers, adapters, executor, runtime, driver) from
scratch. This was true before A-010/B-012 and remains true after. It
is the actual reason the goal→plan and plan→execution halves were
never connected: there is no place in the codebase where "connecting
two subsystems" would even happen yet, because nothing assembles the
graph outside of tests.

**Verdict: PARTIALLY COHERENT at the subsystem level, NOT YET COHERENT
as a product control loop.** Individually, every listed capability is
real (not mocked, not faked) and well-evidenced. Collectively, there
is no path — tested or otherwise — from a user's goal to that goal's
actual execution.

---

## 2. End-to-End Control Loop Map

| Transition | Exists? | Actually Wired? | Real or Mocked? | Persisted? | Recoverable? | Security Enforced? | Tested? |
|---|---|---|---|---|---|---|---|
| User Goal → GoalPlanner | Yes | **No entry point calls it** | Real (any caller) | N/A (input) | N/A | N/A | Only via hand-wired test |
| GoalPlanner → validated Plan | Yes | Yes (internal to planner.py) | Real | N/A | N/A | Validation only (shape/JSON), no auth concept | Yes, 14 unit tests |
| validated Plan → PlanRepository | Yes | Yes | Real (SQLAlchemy) | **Yes** | Yes (repo is stateless/reloadable) | N/A | Yes |
| PlanRepository → PlanExecutor/Runtime | Yes (Executor) / **No (Runtime)** | Executor: yes. Runtime: **never** | Executor: real | Yes (Executor) | Yes (plan recovery test, single-process reload) | N/A | Executor: yes. Runtime bridge: **no test exists because no code exists** |
| RuntimeDriver → per-turn context provider | Yes | Yes (A-009) | Real | Turn-level, yes | Yes (resume test) | N/A | Yes, 7 unit + 1 live-composition test |
| context provider → dynamic tool offering | Yes | Yes (A-008/B-011) | Real | Yes (on Turn) | Yes | N/A | Yes |
| dynamic tool offering → ModelGateway | Yes | Yes | Real (Groq, live-gated) | Yes | Yes | N/A | Yes (B-009 live test, gated) |
| ModelGateway → real model | Yes | Yes | Real, but **no GROQ_API_KEY in this environment** | Yes | Yes | N/A | Gated skip, not fabricated |
| model → permission evaluation | Yes | Yes (B-012, inside `ToolExecutorService.execute`, before dispatch) | Real | Verdict not separately persisted; only the resulting DENIED `ToolResult` is | Yes (it's just a Turn observation) | **Yes — regex/heuristic, not a policy engine** | Yes, 8 unit + 5 integration; **no test drives this through RuntimeDriver/AgentRuntime**, only direct `ToolExecutorService.execute()` calls |
| permission evaluation → ToolExecutor | Yes | Yes, unconditionally (secure-by-default: `DefaultPermissionPolicy()` is the constructor default) | Real | N/A | N/A | Yes | Yes |
| ToolExecutor → filesystem/shell tool | Yes | Yes | Real | Yes | Yes | WorkspaceBoundary (path escape) + permission regex | Yes (B-010/B-011) |
| tool → Observation | Yes | Yes | Real | Yes (on Turn.tool_calls) | Yes | N/A | Yes |
| Observation → next model turn | Yes | Yes **except on denial/failure** | Real | Yes | Yes | N/A | Yes |
| → completion | Yes | Yes | Real | Yes | Yes | N/A | Yes |
| → checkpoint/recovery | Yes | Yes | Real | Yes | Yes (cross-process recovery test) | N/A | Yes |

Two rows carry the entire verdict: **"PlanRepository → PlanExecutor/
Runtime"** (Runtime side never wired) and **"Observation → next model
turn"** (a tool *denial* is indistinguishable from a tool *failure* to
`RuntimeDriver.tool_failed()`, so it halts the task rather than giving
the model a chance to react — see §5).

---

## 3. Goal-to-Plan Assessment

- **Real user goal entry path: does not exist.** `GoalPlanner` is
  constructed only inside `tests/unit/planning/test_planner.py` and
  `tests/integration/planning/test_goal_to_plan_live.py`. There is no
  application/CLI layer that accepts a goal string from anywhere and
  calls `GoalPlanner.plan_goal()`.
- **Reachability from the control plane: not reachable**, because
  there is no control plane entry point for anything in this
  repository yet (see §1).
- **Same domain Plan PlanExecutor uses:** yes, confirmed by code
  inspection — `GoalPlanner._build_plan()` constructs
  `core.planning.models.Plan`/`PlanStep` directly, the identical type
  `PlanExecutor` consumes. No second Plan model exists.
- **Persisted:** yes — `GoalPlanner.plan_goal()` calls
  `PlanExecutor.start_plan()`, which validates the dependency graph
  and calls `PlanRepository.create()` in one step. Verified by test
  (`repo.get(plan.plan_id)` round-trips).
- **Validation before persistence:** yes, and in the correct order —
  JSON/shape validation happens in the planner before
  `PlanExecutor.start_plan()` is even called; `start_plan()` then
  re-validates the dependency graph and only persists if that passes.
  A rejected plan (malformed JSON, missing fields, duplicate step_id,
  cycle, unresolved reference) is never written to the repository —
  verified explicitly in 8 of the 14 unit tests via
  `repo.list_for_goal(...) == []` after the expected exception.
- **Transition into execution without an alternate execution path:**
  moot — there is currently **no** execution path from a generated
  Plan at all, alternate or otherwise. `PlanExecutor.select_next_step`/
  `start_step`/`complete_step` are pure state-machine calls; nothing
  invokes them automatically after `plan_goal()` returns, and nothing
  connects a step's execution to a real tool call. A caller would have
  to manually drive `PlanExecutor` (as the unit tests do) with no
  actual tool/model behind it, or manually drive `RuntimeDriver`
  (as B-009/B-011 do) with no `Plan` behind it. These are not two ends
  of one path today; they are two separate paths.
- **Live proof gap materiality:** the live test
  (`test_real_goal_becomes_a_real_persisted_plan_via_real_groq`) is
  honestly gated and currently skipped (no `GROQ_API_KEY` in this
  environment, same as every other live-gated test in this suite —
  consistent, not a new gap). This gap is real but **secondary** to
  the wiring gap above: even with a live key, a successfully generated
  live Plan still could not be executed by anything in this
  codebase today.

**goal → plan generation** is a solid, real capability.
**goal → plan → actual runtime execution** does not exist. The brief's
warning not to conflate the two is well-founded — they are not
currently on a spectrum of "more or less proven," they are
disconnected.

---

## 4. Permission Enforcement Assessment

- **Operations actually permission-checked:** only `run_command`
  (`DefaultPermissionPolicy._SHELL_TOOLS = {"run_command"}`).
  Filesystem tools (`read_file`, `write_file`, `list_directory`) are
  explicitly *not* passed through the regex policy — they rely
  entirely on `WorkspaceBoundary` (B-010's path-escape check), which
  the policy's own docstring acknowledges rather than duplicates.
  This is a reasonable "don't build a second boundary mechanism"
  choice, but it means the permission *policy object* only ever
  evaluates one tool family.
- **Where the check occurs:** inside `ToolExecutorService.execute()`,
  after tool-registry lookup (so an unknown tool still reports
  `NOT_FOUND` rather than a confusing denial) and strictly before
  `tool.execute()` is invoked on the thread pool.
- **Denial before execution:** yes, confirmed by
  `test_denied_delete_remote_branch_never_executes`, which uses a
  marker-file side effect to prove the shell command never ran, not
  merely that a DENIED verdict was returned.
- **Filesystem boundaries:** enforced by the pre-existing
  `WorkspaceBoundary` (B-010), unchanged by B-012, and B-012's own
  scope statement correctly declines to re-implement it.
- **Shell restrictions actually active:** three deny-classified regex
  categories (delete remote branch, production migration/secret
  export via `cat`/`printenv`/`echo`) and three ask-classified
  categories treated as hard denials for now (install package, push
  branch, any of `curl`/`wget`/`Invoke-WebRequest`/`iwr`), because no
  approval/ask mechanism exists to route the latter through instead.
  Everything else matching `run_command` is allowed by default
  ("secure by default" only in the narrow sense that the *default
  policy instance* is always attached — the *rule set itself* is an
  allow-list-by-omission for shell commands not matching any pattern).
- **Applies through the normal RuntimeDriver path:** **yes by
  construction, but not empirically proven end-to-end.** By
  inspection: `ToolExecutorService.__init__` defaults
  `permission_policy` to `DefaultPermissionPolicy()` whenever no
  policy is passed, and the real `ToolPortAdapter` (used by every
  `RuntimeDriver`/`AgentRuntime` wiring in the live tests) is always
  constructed on top of a `ToolExecutorService`. There is no second,
  policy-free construction path visible anywhere in `src/`. However,
  **B-012's own test suite never drives a denial through
  `RuntimeDriver`/`AgentRuntime`/a model turn** — both the 8 unit
  tests and the 5 integration tests call
  `ToolExecutorService.execute()` directly. The claim "the normal path
  is protected" rests on code inspection of the constructor default,
  not on a composition test analogous to B-011's or A-009's
  `..._through_runtime_driver` test. This is a real, closable gap, not
  a hypothetical one.
- **Can model-generated tool calls bypass permission evaluation?**
  No bypass exists in the code as written — every `ToolCall` reaching
  `ToolExecutorService.execute()` is evaluated before dispatch,
  regardless of caller. The risk is not a code-level bypass; it's that
  this has not been *proven* under the real model/dynamic-tool-
  offering path, only asserted by inspection.
- **What remains unprotected:** everything not `run_command` and not
  already covered by `WorkspaceBoundary`. There is no tool-generic
  permission concept (e.g. filesystem `write_file` outside the
  workspace is caught by `WorkspaceBoundary`, but nothing in the
  *permission* layer would catch, say, an oversized or
  resource-exhausting shell command that doesn't match any of the six
  regexes). The regexes themselves are openly acknowledged in the
  code's own docstring as evadable by a sufficiently obfuscated
  command (e.g. `git push origin --de''lete x`, base64-encoded
  `printenv`, or a script file that does the export instead of an
  inline shell one-liner).

**ENFORCED NOW:** deny for the three named deny categories; effective
deny (labelled "pending approval") for the three named ask categories;
`WorkspaceBoundary` for all filesystem paths. **DEFERRED:** a real
approval/ask workflow, a policy engine beyond regex matching, coverage
of tools other than `run_command`, and empirical (not just
constructor-default) proof that the policy is unbypassable through the
live model path.

---

## 5. Control-Loop Coherence

Classification: **NOT YET COHERENT** — not because any individual
segment is broken, but because the loop as drawn in the brief has a
hard break at exactly one seam and a soft break at another:

**Hard break:** `PlanRepository → PlanExecutor / Runtime`. As
established in §1/§3, no code connects a `Plan`'s steps to
`AgentRuntime`/`RuntimeDriver` turns. The "goal → plan" half and the
"runtime → completion" half are both individually coherent internally,
but the diagram in the brief is not one path in this codebase — it is
two paths that happen to be drawn end-to-end in the brief's diagram.

**Soft break, worth naming precisely because the brief asks for it:**
"whether permission denial produces an observation/error that the
model/runtime can handle." Technically yes — `ToolPortAdapter` maps
`ToolOutcome.DENIED` to `{"status": "error", ...}`, the same shape any
other tool error takes, so nothing crashes and the denial is a normal,
persisted `Turn.tool_calls[i]["observation"]`. But
`RuntimeDriver.tool_failed()` treats *any* `status == "error"`
observation — a denial included — as cause to stop the entire task
(`DriverOutcome.STOPPED_TOOL_FAILURE`), not to continue to a further
model turn where the model could see the denial and try something
else. This predates B-012 (it's ADR-038's original, deliberately
simple policy), but B-012 changes what triggers it in practice: a
permission denial is now a plausible, expected event during normal
operation (not just a genuine tool bug), and today it always ends the
task rather than becoming information the agent can act on. Whether
that's the *right* behavior for a denial specifically (fail closed and
stop, vs. inform-and-continue) is a real design question this review
surfaces but does not resolve.

Everything else the brief asks to pay attention to checks out cleanly:
dynamically offered tools (`ToolOfferingResolver` via A-008/A-009's
context provider) are the exact same tools the permission policy
governs (`_SHELL_TOOLS`/`WorkspaceBoundary` match the concrete tool
names `ToolExecutorService` dispatches to — no separate offering-time
vs. execution-time tool identity split), and completion/checkpoint
semantics are unchanged by either A-010 or B-012 (neither touches
`AgentRuntime`, confirmed by the git diff for both commits touching
only `core/planning/*`, `tests/*`, and
`neptune/infrastructure/{security,tools}/*`).

---

## 6. Real Coding-Agent Capability

| | Status |
|---|---|
| Accept a meaningful user objective | **TECHNICALLY PROVEN** only in the sense that `GoalPlanner.plan_goal(Goal(...))` works when called by hand. No path exists for an actual user to supply one. |
| Create a useful plan | TECHNICALLY PROVEN (mock + structurally sound; live proof pending a key). Plan *quality* is untested — no test asserts the plan is a *good* decomposition, only that it's structurally valid. |
| Inspect a workspace | TECHNICALLY PROVEN (`list_directory`/`read_file`, B-010/B-011), but the model gets zero workspace context automatically (§9) — it must already know to ask. |
| Modify files | TECHNICALLY PROVEN, real writes inside a `WorkspaceBoundary` (B-011's real file-write proof, still passing). |
| Execute shell commands | TECHNICALLY PROVEN, now permission-gated for the three named risk categories. |
| Respect current permission policy | TECHNICALLY PROVEN for `run_command` at the `ToolExecutorService` level; not proven through the live model/RuntimeDriver path (§4). |
| Observe results | TECHNICALLY PROVEN — every tool call's result is a persisted observation. |
| Continue iteratively | TECHNICALLY PROVEN up to `max_turns`, and up to the first denied/failed tool call, which currently ends the task rather than continuing (§5). |
| Recover state | TECHNICALLY PROVEN — genuine two-process recovery tests exist for runtime turns, driver resume, and plan step persistence independently. |
| Complete the task | TECHNICALLY PROVEN for the runtime half; **not connected** to a plan's completion (a `Plan` has no "done" callback into `AgentRuntime.complete_task`). |

**USEFUL FOR A REAL CODING WORKSPACE:** not yet, and not primarily
because any one capability is weak — because there is no assembled
product a person could point at a real repository and run. Every
capability above is reachable only by writing a new Python script that
hand-wires the same dependency graph the tests already hand-wire.

**PRODUCTION-GRADE CODING AGENT:** no — no approval workflow, no
sandbox/container isolation (explicitly deferred, not attempted, per
`07_SECURITY/01_THREAT_MODEL.md`'s still-frozen `SANDBOX_CONTRACT`),
heuristic (not policy-engine) permission enforcement, no repository
context intelligence, and no entry point.

---

## 7. Security Gap Assessment

The single most consequential unresolved gap is **the absence of any
approval ("ask") workflow**, which cascades into a second-order
correctness problem: because there is nowhere to route an "ask"
decision, B-012 collapses `ask` into `deny`. Per
`07_SECURITY/02_PERMISSION_MODEL.md`'s own stated precedence
(`EXPLICIT APPROVAL` sits *above* `ALLOW RULE`, and the model
document explicitly lists `install package`, `network access`, and
`push branch` as `ask`, not `deny`), the current system is *more
restrictive* than the design it implements — which is the safe
direction to err in the absence of an approval mechanism, and B-012's
own code comments say so honestly rather than hiding it. But it means
a category of genuinely useful, low-risk agent actions (installing a
declared dependency, pushing a feature branch) is currently
unconditionally blocked with no path to "yes, do it" short of a code
change. This is more consequential right now than sandbox/isolation
(also missing, also explicitly deferred, but the codebase has never
claimed otherwise) because it's the gap most likely to make the
*existing* enforced categories feel broken to a real user, not just
incomplete.

Named but secondary: heuristic regex matching for shell denial is
openly documented as evadable, not a policy engine; no sandbox/
container isolation exists at all (frozen `SANDBOX_CONTRACT`); no
secret-scanning beyond the one `_EXPORT_SECRET` regex pattern; no
symlink-attack handling was inspected in `WorkspaceBoundary` as part
of this audit (out of this review's scope to verify further, flagged
for a future audit, not investigated here since B-010/B-011 already
passed their own review and this audit's brief scopes attention to
what changed).

---

## 8. Planning Gap Assessment

The single most usefulness-limiting gap in Planning is **the wiring
gap already established in §1/§3/§5** — no amount of plan-quality
improvement matters yet because no plan currently executes. Once that
wire exists, the next-most-material gap (in order the product would
actually hit them) is: no failed-step recovery or replanning — if a
`PlanStep` fails, `PlanExecutor.fail_step()` cascades `SKIPPED` to
everything depending on it and the plan simply ends up incomplete;
nothing re-invokes `GoalPlanner` with the failure as new context, and
nothing lets the model see a failed step and propose a plan
modification. Goal decomposition quality (is the model's plan any
*good*) is real but tertiary — a mediocre plan that executes and can
be corrected is more valuable right now than a better plan generator
bolted onto still-nonexistent execution.

---

## 9. Context / Repository Intelligence

`core/runtime/context.py::assemble_context()` feeds the model exactly:
task id, session id, agent id, task status, `task.requirements`,
`task.constraints`, and up to the last 5 events
(`_MAX_RECENT_EVENTS_IN_PROMPT` in `model_gateway_adapter.py`). There
is **no workspace/repository awareness of any kind** — no file tree,
no directory listing, no file content, no git status — fed to the
model automatically. The model must already know to call
`list_directory`/`read_file` blind, with zero orientation, on every
fresh task. This matches the module's own docstring, which explicitly
scopes this out ("Deliberately NOT full context/repository
indexing... explicitly excludes that from this stage") — so this is a
known, named limitation, not a silent gap.

The smallest missing context capability that would materially help:
an initial, automatic workspace snapshot (e.g. a shallow
`list_directory` of the workspace root, or a small file tree) injected
into `assemble_context()`'s output on the first turn of a task whose
tools include the filesystem family — not full repository indexing
(explicitly out of scope), just removing the "the model doesn't know
there's a repository here at all until it guesses to look" problem.

---

## 10. Production Hardening

Scoped to what actually changed or matters now, not a general
wishlist:

- **Malformed model output:** now handled twice, independently, for
  the two paths that can receive it — `GoalPlanner` rejects malformed
  JSON/plan shape without persisting (A-010), and
  `ModelGatewayAdapter._error_response()` already normalized gateway
  failures to a non-raising dict (ADR-045, pre-existing). No shared
  helper exists between the two, though the failure modes are
  different enough (JSON-shape validation vs. gateway-level error)
  that this isn't necessarily a real duplication yet.
- **Concurrency:** `ToolExecutorService` bounds tool execution to a
  4-worker thread pool with a timeout (pre-existing, B-010); B-012
  adds no new concurrency surface (`PermissionPolicy.evaluate()` is a
  synchronous, in-process regex check with no I/O).
- **Retry/backoff, provider failure handling:** unchanged by this
  milestone; still whatever ADR-045 established.
- **Observability:** permission denials are visible only as a
  generic `status: "error"` observation with `error_message` — nothing
  distinguishes "denied by policy" from "tool crashed" at the
  `RuntimeDriver`/`Turn` level except reading the error string. A
  caller inspecting `turn.tool_calls[i]["observation"]["outcome"]`
  *can* tell (`"denied"` vs `"error"`/`"timeout"`), since
  `ToolPortAdapter` does pass through `result.outcome.value`
  unchanged — so the information exists, it's just one field, not a
  distinct status the driver's own policy currently branches on
  (§5).
- **Secrets:** the one `_EXPORT_SECRET` regex is a partial mitigation,
  not the `07_SECURITY/04_SECRETS.md`-scoped secret-handling story
  (not inspected further in this audit — out of this milestone's
  changed surface).

Nothing in A-010/B-012 introduced a new resource/cost-control gap
beyond what already existed.

---

## 11. Free/Cheap-First Verification

Preserved structurally. `src/neptune/infrastructure/providers/`
contains exactly `groq_adapter.py` and `reference_adapter.py` — no new
provider was added by A-010 or B-012. `GoalPlanner` depends only on
`core.contracts.gateway.ModelGatewayPort` (the same opaque-dict
contract everything else uses); it does not import Groq, does not
special-case a model/provider, and does not add a routing constraint
that would require a paid tier (`RoutingConstraints.cost_class_max`
defaults to `CostClass.FREE`, unchanged). `DefaultPermissionPolicy` is
pure in-process regex evaluation — no provider dependency, no cost.
**No paid-only assumption was introduced.** The one caveat, unchanged
from prior reviews: Groq remains the *only* real (non-reference)
provider actually implemented, so "provider independence" is proven
architecturally (the abstraction exists and nothing depends on Groq
directly outside its own adapter) but not yet empirically by a second
real provider.

---

## 12. Single Dominant Product Bottleneck

**Goal → execution integration** — specifically, the complete absence
of any code path connecting `GoalPlanner`'s output to
`AgentRuntime`/`RuntimeDriver`, compounded by the absence of any
product entry point at all. This is chosen over the other real
candidates (approval workflow, repository context, plan-quality/
replanning) because every one of those improves a capability that
currently has no consumer: a better plan generator, a richer approval
model, or better workspace context all bolt onto a wire that does not
exist yet. Building any of them before the wire exists optimizes a
subsystem the product still can't actually run end-to-end.

---

## 13. Single Recommended Next Milestone

**Name:** `NEPTUNE-[A/SEQ]-011 — Plan-Driven Task Execution (Single Entry Point)`

**Objective:** Wire an existing `Plan` (from `GoalPlanner` or a
hand-built one) into a real, running `AgentRuntime`/`RuntimeDriver`
execution, one step at a time — the smallest bridge that makes
`PlanExecutor`'s `select_next_step()`/`start_step()`/`complete_step()`/
`fail_step()` lifecycle actually drive real turns instead of being
manually called by a test — and give it exactly one real entry point
(even a bare script under a new `src/interfaces/` or `src/cli/`, not a
full CLI framework) that takes a goal string and runs it, so this
capability is reachable by something other than a test file for the
first time in the project's history.

**Prerequisites:** none beyond what's already merged — A-010,
B-012, A-009's context-provider seam, and the existing
`PlanExecutor`/`AgentRuntime` are all individually sufficient
building blocks.

**Exact problem solved:** closes the hard break identified in §1/§5 —
the one thing standing between "two well-tested subsystems" and "a
coherent control loop."

**What it unlocks:** every downstream item in §8/§9/§10 becomes
worth investing in, because there would finally be a running loop for
plan quality, replanning, repository context, and approval workflows
to improve.

**What explicitly waits:** repository/workspace context injection
(§9), replanning/failed-step recovery (§8), an approval/ask mechanism
(§7), a second real provider, and anything sandbox-related. None of
these should be pulled forward into this milestone — the brief for
A-010 already correctly scoped "the plan does not need to execute in
this task," and this next milestone is exactly the task that changes
that, and only that.

**Owner:** a **single-owner sequential task**, not parallel A/B work.
This milestone necessarily touches the seam between Claude A's
territory (`PlanExecutor`, `AgentRuntime`, `RuntimeDriver`) on both
sides at once — there is no clean split where one lane could own "plan
side" and the other "runtime side" without one blocking on the other's
in-progress interface the entire time, which is exactly the kind of
tight coupling the two-lane methodology (ADR-035) was designed to
avoid pairing on. Recommend Claude A owns it end-to-end, the same way
A-009 (a similarly cross-cutting seam) was single-owner despite
touching what B-011 had already built on.

---

## 14. A/B Process Assessment

The two-worker split continues to work well for what it was designed
for: A-010 and B-012 touched **zero overlapping files**
(`git show df2b65e --stat` shows a clean, conflict-free merge), and
neither task touched `DEVELOPMENT_STATE/assignments.yaml`,
`decisions.yaml`, `workers.yaml`, or `05_DECISIONS/00_ADR_INDEX.md` —
the shared-bookkeeping freeze introduced for this round was fully
effective, evidenced by the merge commit containing only the 6
B-012-authored files with no bookkeeping diff at all.

However, this review is itself evidence that the split is starting to
strain at exactly the seam identified in §12/§13: A-010 (Claude A) and
B-012 (Claude B) were both scoped, correctly, to *not* wire themselves
into each other or into the runtime — which is why the merge was
clean — but it also means neither lane was responsible for noticing
that "goal → plan" and "plan → execution" had never been connected at
all. That's a gap the two-lane split is not well-suited to catch on
its own, because it lives *between* the lanes' scopes, not inside
either one. The minimum process change: the next cross-cutting
integration milestone (§13) should be explicitly called out as
single-owner/sequential in its authorization, as this review
recommends, rather than left to whichever lane happens to pick it up
next — not a redesign of the methodology, just consistent labeling of
which tasks are lane-work vs. seam-work going forward.

---

## 15. ADR / Decision Review

No ADR was created or renumbered as part of this review, per its
explicit scope.

- **A-009 / Review 004's RuntimeDriver context-provider decision:**
  recommend formalizing. It is a genuine, already-implemented
  architectural decision (an injected `Callable[[], dict]` seam) with
  no existing ADR covering it — ADR-038 covers `RuntimeDriver`'s
  complete/continue/fail *policy*, not the context-provider
  *mechanism*. The prior chat already proposed a title
  ("RuntimeDriver Per-Turn Context Supplementation via Injected
  Context Provider") pending your number confirmation; this review
  concurs it is worth formalizing, not busywork.
- **A-010's structured-planning decision:** worth formalizing, lower
  urgency than the above. The design choice worth recording is
  narrow but real: using the model response's existing opaque
  `content` field for structured plan JSON rather than extending the
  tool-calling mechanism or the unimplemented
  `RoutingConstraints.require_structured_output` flag. It's a small
  decision, but it's the kind of "why didn't we use the mechanism that
  looks like it should exist" question a future implementer will
  plausibly ask, given `require_structured_output` sits right there
  in the contract.
- **B-012's permission behavior:** **not adequately covered by
  existing decisions**, and this is the one I'd flag as most worth an
  ADR of the three, precisely because it's a security-relevant
  decision, not just an implementation-mechanism one: the choice to
  collapse `ask` into `deny` in the absence of an approval mechanism
  (§7) is exactly the kind of decision a future contributor could
  reverse by accident (e.g. "helpfully" relaxing `ask` categories to
  `allow` without realizing the design intent was "deny until approval
  exists," not "deny forever"). ADR-038 (Runtime Driver policy) and
  ADR-040 (Plan executor policy) are the nearest existing decisions
  and neither covers this. Recommend a title along the lines of
  "Permission policy: `ask`-classified actions denied pending approval
  mechanism (B-012)."

No numbers are assigned or invented here, per this task's explicit
scope; these are recommendations only, sequenced after whatever number
ADR-047 (already proposed for A-009 in the prior session) ends up
being confirmed as.

---

## 16. Test Evidence

Full suite, run against this branch at `df2b65e` with Postgres up
(`docker compose up -d`, no `GROQ_API_KEY` set in this environment):

```text
collected: 341
passed:    333
failed:    0
skipped:   8
```

All 8 skips are the live-Groq-credential guard
(`GROQ_API_KEY not set`) on the pre-existing B-009 full-live-loop test,
this session's own A-010 live goal-to-plan test, and the small number
of other live-gated tests already in the suite before this milestone —
no new, unexplained skip reasons were introduced.

**This does not match the number this review's authorization brief
stated as the current baseline (`383 passed, 38 skipped, 0 failed`).**
I want to flag that discrepancy plainly rather than either silently
substituting my number for the brief's or silently reporting the
brief's number as if I'd verified it: `pytest tests -q --collect-only`
on this exact checkout reports **341 tests collected**, matching
333+8 exactly; `git status` is clean (no uncommitted test files); and
`git log` confirms `HEAD` is `df2b65e`, the exact commit the brief
names as the merge target. I do not have a confirmed explanation for
the gap (421 vs. 341 total) — possibilities include the brief's figure
coming from a different environment (e.g. one with `GROQ_API_KEY` set,
though that would be expected to *lower* the skip count, not raise it
to 38, so this doesn't fully explain it either), a different branch
state at the time the brief was written, or a transcription error. I
am reporting the number I actually measured on the actual checked-out
commit rather than reconciling it to the brief's stated figure, per
this review's own instruction not to assume test-count claims are
accurate without verification.

Targeted subsystem runs (all included in the full-suite number above,
re-run in isolation for this review's own verification):

```text
tests/unit/planning + tests/unit/security +
tests/integration/tools/test_permission_enforcement.py +
tests/integration/runtime + tests/unit/runtime/test_driver.py +
tests/integration/planning
  → 67 passed, 3 skipped (0 failed)
```

- A-010 planner tests: 14/14 passed (`tests/unit/planning/test_planner.py`).
- B-012 permission tests: 13/13 passed (8 unit + 5 integration).
- B-011 real coding-agent composition test: passed, including the
  A-009 follow-up
  (`test_full_agent_loop_with_real_dynamic_offering_through_runtime_driver`).
- RuntimeDriver context-provider tests: 7/7 passed
  (`tests/unit/runtime/test_driver.py`'s A-009 section).
- Recovery tests: plan-recovery (2-process) and driver-resume tests
  both passed.

No live-provider result is claimed or fabricated anywhere in this
review; every live-gated assertion above is reported as skipped, with
its actual skip reason, not as passed.

---

## 17. Final Verdict

```text
PROCEED WITH CORRECTIONS
```

Not `REWORK REQUIRED`: nothing that has been built is wrong, mocked,
or falsely claimed — A-010 and B-012 are each exactly what their
briefs asked for, cleanly merged, fully tested within their own scope,
and honestly reported (including their own honest gaps, like A-010's
pending live proof). Not `PROCEED` unqualified: this review's central
finding — no code path exists from a generated Plan to actual
execution, and no product entry point exists at all — is a correction
significant enough that continuing to add capability on either side of
that seam (more planning quality, more permission categories, more
tools) before closing it would compound the gap rather than the
product. The correction is narrow and already scoped in §13: one
single-owner milestone to wire `Plan` execution through
`AgentRuntime`/`RuntimeDriver` and give the result one real entry
point.

---

# Final Report

```text
STATUS: DIRECTOR_REVIEW_005.md written, committed, pushed. Read-only —
        no implementation, contract, planning, permission, RuntimeDriver,
        tool, provider, or Bible changes made.

COMMIT: (see push output)

FILES CREATED/CHANGED: DIRECTOR_REVIEW_005.md only (repo root).

END-TO-END COHERENCE RESULT: PARTIALLY COHERENT at the subsystem
    level; NOT YET COHERENT as a product control loop. Hard break:
    PlanRepository -> PlanExecutor/AgentRuntime (zero wiring anywhere
    in src/ or tests/). Soft break: RuntimeDriver.tool_failed() cannot
    distinguish a permission denial from a genuine tool failure, so a
    denial always halts the task rather than becoming something the
    model can react to.

GOAL-TO-PLAN RESULT: goal -> plan generation is real, validated,
    persisted, and tested (14 unit tests + 1 honestly-skipped live
    test). goal -> plan -> execution does not exist in any form --
    zero code connects PlanExecutor to AgentRuntime/RuntimeDriver.
    GoalPlanner is unreachable from any product entry point because
    no product entry point exists.

PERMISSION RESULT: real, enforced before tool dispatch, secure-by-
    default at the ToolExecutorService constructor level, verified to
    block side effects (marker-file test), correctly conservative
    (ask -> deny-pending-approval rather than silently allowing).
    Gaps: only run_command is policy-checked (filesystem relies on
    pre-existing WorkspaceBoundary); heuristic regex, not a policy
    engine, openly documented as evadable; the "applies through the
    normal RuntimeDriver path" claim rests on constructor-default
    inspection, not an empirical composition test through a real
    model turn.

REAL CODING-AGENT RESULT: every individual capability (accept a goal,
    plan, inspect workspace, modify files, run shell commands,
    respect permissions, observe, iterate, recover, complete) is
    TECHNICALLY PROVEN in isolation. Not yet USEFUL FOR A REAL CODING
    WORKSPACE because nothing assembles these into one runnable path
    outside test files, and plan generation still cannot reach
    execution at all. Not PRODUCTION-GRADE: no approval workflow, no
    sandbox, heuristic-only permission enforcement, no repository
    context.

SECURITY GAP: absence of any approval/"ask" workflow, which forces
    B-012 to collapse ask-classified actions (install package, push
    branch, network access) into denial -- safe-direction but more
    restrictive than 07_SECURITY/02_PERMISSION_MODEL.md's own stated
    design, and the gap most likely to visibly limit real usage first.

PLANNING GAP: goal->execution wiring dominates (see bottleneck);
    secondary gap is no failed-step recovery/replanning -- a failed
    PlanStep cascades SKIPPED with no path back to GoalPlanner or the
    model for correction.

CONTEXT GAP: assemble_context() feeds task requirements/constraints/
    recent events only -- zero automatic workspace/repository
    awareness (explicitly scoped out by its own docstring, not a
    silent omission). Smallest missing piece: an initial shallow
    workspace listing injected on a task's first turn.

PRODUCTION HARDENING STATUS: no new gaps introduced by A-010/B-012.
    Malformed model output now double-handled (gateway-level +
    planner-level, independently, no shared helper). Permission
    denial is distinguishable from other tool failures at the
    ToolResult.outcome level, but RuntimeDriver's policy doesn't yet
    branch on that distinction.

FREE/CHEAP-FIRST STATUS: preserved. No new provider, no paid-only
    assumption, GoalPlanner and DefaultPermissionPolicy both provider-
    agnostic. Groq remains the only real (non-reference) provider
    implemented -- architecturally proven independence, not yet
    empirically proven by a second real provider.

SINGLE DOMINANT BOTTLENECK: goal -> execution integration -- the
    complete absence of any wiring between GoalPlanner's output and
    AgentRuntime/RuntimeDriver, compounded by the absence of any
    product entry point.

SINGLE NEXT MILESTONE: Plan-Driven Task Execution (Single Entry
    Point) -- wire PlanExecutor's step lifecycle to real
    AgentRuntime/RuntimeDriver turns and add exactly one real entry
    point. Single-owner sequential task (Claude A), not parallel A/B
    work -- this seam sits between both lanes' existing scopes.

A/B PROCESS RESULT: shared-bookkeeping freeze fully effective this
    round (zero overlapping files, zero bookkeeping-file diffs, clean
    merge). Minimum recommended change: explicitly label cross-
    cutting seam milestones (like the one recommended above) as
    single-owner in their authorization, since lane-scoped tasks are
    structurally unlikely to notice a gap that lives between lanes.
    No methodology redesign recommended.

ADR / DECISION RESULT: no ADR created or renumbered (out of scope).
    Recommend formalizing, in this priority order: (1) B-012's
    ask-denied-pending-approval decision -- highest priority, security-
    relevant and reversible-by-accident if undocumented; (2) A-009's
    RuntimeDriver context-provider decision (already proposed, title
    on file, awaiting your number confirmation); (3) A-010's
    content-field-for-structured-output decision -- lower urgency.
    No numbers assigned or invented.

TEST RESULTS: collected 341, passed 333, failed 0, skipped 8 (all
    live-GROQ_API_KEY guards, no unexplained skips), Postgres live via
    docker compose. This does NOT match this review's own
    authorization brief's stated baseline of 383 passed / 38 skipped;
    flagged explicitly in section 16 as an unreconciled discrepancy
    rather than silently overwritten in either direction. HEAD
    verified at df2b65e, git status clean, 341 collected confirmed by
    --collect-only.

FINAL VERDICT: PROCEED WITH CORRECTIONS.

OUT OF SCOPE CONFIRMATION: no implementation, contract, planning,
    permission, RuntimeDriver, tool, or provider code modified; no
    Bible content modified; no ADR created or renumbered; no shared-
    state file (assignments.yaml, decisions.yaml, workers.yaml,
    00_ADR_INDEX.md) modified; no recommended milestone started. Only
    DIRECTOR_REVIEW_005.md was created.
```
