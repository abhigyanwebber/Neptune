# DIRECTOR_REVIEW_007 — Integrated Product-Readiness Review (post A-011 / B-013)

Audit only. No source, contract, planning, runtime, gateway, registry,
permission, tool, or Bible file was modified. No ADR created.
Audited commit: `51a9757` (`origin/main`, includes A-011 and B-013).
Numbering note: `DIRECTOR_REVIEW_006.md` is A-011's report and
`DIRECTOR_REVIEW_006B.md` is B-013's; this review is 007 to avoid a third
"006".

## 1. Bottom line

**No. A user cannot submit a goal to Neptune today.** There is no entry
point of any kind. Every link of the goal-to-completion chain exists as
real, tested code, but the chain only runs inside test files that
hand-build the dependency graph. The distance to an MVP is small in
component count and concentrated in one place: the missing composition
root, plus three known gaps that only matter once something can run it.

## 2. Test baseline — the quoted numbers are misleading

I ran the suite twice.

| Run | Collected | Passed | Failed | Skipped |
|---|---|---|---|---|
| As found (Neptune Postgres not running) | 359 | 317 | 0 | 42 |
| With `docker compose up -d` | 359 | 350 | 0 | 9 |

The brief's 317/42 is the first row. Skip classification:

- **9 skips: `GROQ_API_KEY` not set** (all live-model tests).
- **33 skips: "Postgres not reachable"**, not credential guards. Docker was
  running only unrelated `icpe-*` containers; Neptune's own container had
  stopped.

The brief's premise that "most skips are live-provider guards" is wrong for
that run: about 79% were a stopped database. In that state the suite still
reports 0 failures while silently skipping **every** real-tool integration
proof, including all of A-011's and the recovery tests. A green run without
Postgres proves much less than it appears to. All numbers here are
mine, from this session.

## 3. What A-011 fixed, and what it did not

Fixed: `PlanRunner.run_goal` (`src/core/planning/plan_runner.py`) connects
`GoalPlanner.plan_goal` to `PlanExecutor` and to
`RuntimeDriver.execute_task`, one fresh task per step, and maps outcomes to
`complete_step`/`fail_step`. That closes Review 005's "no code connects the
Plan to the runtime" finding. Verified by reading it and by
`tests/integration/planning/test_goal_to_execution.py` (passes with
Postgres).

Not fixed, and still true: **no product entry point exists.** Searched the
repo for `__main__`, argparse/click/typer, fastapi/flask/uvicorn, `main`/
`cli`/`app`/`server` files, `pyproject`, Dockerfile, Makefile. Only hits:
three scripts under `scripts/` with `if __name__ == "__main__"`.
`scripts/run_live_first_agent_turn.py` is the closest: it drives
`RuntimeDriver` with `max_turns=1`, a hard-coded requirement
(`"Respond with exactly: NEPTUNE_GATEWAY_OK"`), and no tools. It does not
reference `GoalPlanner`, `PlanRunner`, permissions, or approval. Outside
`tests/`, nothing constructs `WorkspaceBoundary`, `RunCommandTool`, or calls
`load_tools`; `GoalPlanner`, `PlanRunner` and `ApprovalProvider` are
referenced only by their own modules.

## 4. The end-to-end path, link by link

Legend: REAL = production code, reachable in normal operation;
INDIRECT = real code, reachable only if a caller hand-builds the graph;
TEST-ONLY = exists only under `tests/`; MISSING.

| # | Link | Where | Status |
|---|---|---|---|
| 1 | User supplies a goal | nothing; tests write `Goal(...)` literals | **MISSING** |
| 2 | Goal reaches GoalPlanner | `PlanRunner.run_goal` -> `GoalPlanner.plan_goal` | INDIRECT |
| 3 | Plan persisted | `plan_goal` -> `PlanExecutor.start_plan` -> `SqlAlchemyPlanRepository.create` | INDIRECT |
| 4 | PlanRunner receives plan | same call, `plan_runner.py::run_goal` | INDIRECT |
| 5 | Step reaches RuntimeDriver | `PlanRunner._run_step` -> `driver_factory(task_id)` -> `execute_task` | INDIRECT for PlanRunner; the `driver_factory` itself is **TEST-ONLY** (`tests/integration/planning/test_goal_to_execution.py::_driver_factory`) |
| 6 | Per-turn context | `RuntimeDriver._run_loop` -> `context_provider()` | mechanism INDIRECT; the provider closures are **TEST-ONLY** |
| 7 | Dynamic tool offering | `ToolOfferingResolver.available_tools`; `ModelGatewayAdapter` reads `request["available_tools"]` | INDIRECT; catalog seeding via `load_tools` is called only from tests: **TEST-ONLY wiring** |
| 8 | Permission evaluation | `ToolExecutorService.execute` -> `DefaultPermissionPolicy.evaluate`, default-on | INDIRECT |
| 9 | ASK approval | `executor.py` ASK branch -> `approval_provider.decide`; default `AutoRejectApprovalProvider` | mechanism INDIRECT; **user-facing channel MISSING** |
| 10 | ToolExecutor runs tool | `ToolExecutorService.execute` | INDIRECT |
| 11 | Observation returns | `ToolPortAdapter` -> `Turn.tool_calls` -> next `run_turn` | INDIRECT |
| 12 | Next turn | `RuntimeDriver._run_loop` | INDIRECT |
| 13 | Step completion | `_run_step` -> `PlanExecutor.complete_step` | INDIRECT |
| 14 | Plan/goal completed | per-step `complete_task`; `Plan` has **no plan-level status field**; completion is derived (`all_succeeded`) and returned in `PlanRunResult`, not persisted as a goal outcome | INDIRECT, partial |

Score: 0 links are usable by an end user without writing new code; 1 is
missing outright; the remainder are real components with no production
composition. "Real" here means implemented and tested, not shippable.

## 5. Cross-step context

**Classification: B (acceptable MVP limitation), with one cheap defect that
should be fixed first.** Not solved elsewhere (C is ruled out: I found no
mechanism that carries state across steps).

What `PlanRunner._run_step` gives a step: `requirements = [step.title,
step.description]` and `constraints = {"capability": ...}` if set. The
runtime context for that task is its requirements, constraints and up to
the last few events **of that task only**.

Lost between steps:

- **The original goal text.** `Goal.description` is never passed to the
  runtime; each step sees only its own title/description. This is the
  defect: a step titled "Read the file and verify it" has no idea what the
  user asked for.
- Other steps' titles (the model can't see the plan's shape).
- The previous step's model messages, tool observations, and final answer.
  These *are* persisted in the database (Turn rows of the previous task)
  but nothing reads them.
- Any information not written to disk. Steps only cooperate through the
  filesystem, which is why the tests pass.
- Approval state: `ApprovalProvider.decide(call, verdict)` has no notion of
  a grant, so an approved ASK is asked again in the next step. (Inferred
  from the protocol signature; not exercised across steps.)

Persistent state that *does* survive: task/session/turn/checkpoint rows,
step statuses, workspace files.

Why B: a plan whose steps agree on file paths (planner-chosen) works.
It becomes a blocker for any plan where step N needs something step N-1
decided or discovered and didn't write down.

## 6. Failure and resume

**Classification: MVP limitation (must be disclosed); full loop resume is
post-MVP.** Scenario: step 1 done, step 2 not started, crash, restart, same
goal.

- *Can Neptune identify the persisted plan?* The data is there
  (`PlanRepository.list_for_goal`, `get`), but `run_goal` takes a `Goal`,
  not a plan id, and never looks.
- *Can it identify the completed step?* Persisted, yes; nothing reads it on
  restart.
- *Can it continue from the correct next step?* Not through any provided
  API. A hand-written loop over the persisted plan
  (`get` + `select_next_step`) would pick step 2 correctly, but no such
  code exists.
- *Can it accidentally repeat step 1?* **Yes.** Re-submitting the goal to
  `run_goal` calls `plan_goal` again, which makes a new model call, creates
  a **new plan** (`<goal>-plan-2`), and re-runs step 1 under a new task id.
- *Worse case:* a crash *during* a step leaves it `RUNNING`.
  `select_next_step` only returns `PENDING` steps and `start_step` rejects
  anything else, so that step and its dependents are stuck with no
  reconciliation path. Re-running the same task id via `execute_task` would
  call `create_task` with an existing primary key (standard SQLAlchemy
  behavior would raise; I did not execute this).
- *Does `execute_until_stop` participate?* Only for a mid-step **task**
  (proven for a plan-step-shaped task id in A-011's test). `PlanRunner`
  never calls it.
- *Cross-process recovery indirectly available?* Two separate proofs exist
  (task-level, and plan-state persistence in `test_plan_recovery.py`) but
  they were never composed.

The README's "a run can stop and resume across process restarts" is true
at task level and not true at goal level.

## 7. Permission and approval

Through the real execution path (A-011 tests, real `ToolExecutorService`,
no policy override):

- **ALLOW** (file writes/reads): proven through `PlanRunner`.
- **DENY**: proven through `PlanRunner`; no side effect, step `FAILED`,
  dependent `SKIPPED`.
- **ASK + APPROVE, ASK + REJECT, approval failure, and default
  fail-closed**: proven only in
  `tests/integration/security/test_ask_approval.py`, which constructs
  `ToolExecutorService` directly (6 tests). None goes through `RuntimeDriver`
  or `PlanRunner`. Structurally it is the same executor, so I expect
  identical behavior, but that is an inference, not a proof.

Whether Neptune has a real approval channel: **no. Only the abstraction.**
The shipped implementations are `AutoRejectApprovalProvider` (production
default, fails closed) and `StaticApprovalProvider`/
`FailingApprovalProvider` (test doubles). Nothing asks a human.
Consequence today: install/push/network commands are always refused, and a
rejected or denied call ends the step (see §10, T6).

## 8. Live-model status

I could not run any live test (`GROQ_API_KEY` not set). Below,
"recorded" means the ledger says an earlier session with a key passed; I did
not re-verify.

| Capability | Real model | Notes |
|---|---|---|
| Groq provider call | recorded (B-003, B-008) | model was swapped once after Groq retired the original (registry churn is real) |
| Real tool call through runtime | recorded (B-009 echo, B-011 filesystem) | B-011 reports real-model variance in tool discovery |
| Dynamic offering with real model | recorded (B-011) | |
| Goal -> Plan with real model | **never run** (A-010 test skips) | |
| Plan execution with real model | **never run** (A-011 test skips) | |
| Permission deny/ASK with real model | **never run** | |

Proven with mock model + real tools + real Postgres: goal -> plan ->
execution -> permission deny -> resume of a plan-step task (A-011 tests).
Unit/isolated only: ASK paths, planner validation edge cases.
Unknown and material: whether a free-tier model reliably emits valid
plan JSON and then completes multi-step plans. Everything about plan
quality is untested.

## 9. Remaining work (finite, MVP-oriented)

MVP definition used: one command takes a goal and a workspace path, plans,
executes with real tools under permission/approval, and visibly succeeds or
fails, on a free provider.

| ID | Task | Why / evidence | Depends on | Parallel-safe? | MVP? | Size |
|---|---|---|---|---|---|---|
| T1 | Composition root + CLI entry point (`neptune run "<goal>" --workspace X`): build registries/seed catalog, gateway, tools, `driver_factory`, `PlanRunner`; print results | §3, §4 link 1/5/6/7; nothing outside tests builds any of it | T2 preferably first | No, single owner | **Required** | MEDIUM |
| T2 | Pass goal text (and prior step outcomes) into each step's context | §5; goal omitted today | none | No (same seam as T1) | **Required** (goal text); prior outcomes recommended | SMALL |
| T3 | Interactive approval channel (CLI prompt implementing `ApprovalProvider`) | §7; only auto-reject exists | T1 | No (lives in T1's CLI) | **Required** for a shell-using agent | SMALL |
| T4 | Live validation with a real key: goal -> plan -> execute, incl. one ASK | §8; three never-run paths | T1, T2, T3, a key | Yes (mostly operator time) | **Required** as the evidence gate | SMALL |
| T5 | Docs/ledger reconciliation: README (says v0.7.1, "no AI-driven plan generation", gateway wiring still to do), `assignments.yaml` missing A-009/A-010/B-012/B-013/Reviews 005-007, ADR decisions pending since Review 005 | evidence: README lines 5/62/70; ledger grep | none | Yes | **Required** for honesty; director-owned | SMALL |
| T6 | Denial/rejection becomes a model-visible observation instead of ending the step | `RuntimeDriver.tool_failed` treats any `status=="error"` as stop | none | Sequential with T2/T1 (both change step behavior) | Recommended | SMALL |
| T7 | Initial workspace snapshot into first-turn context | Review 005 §9; context has no repo awareness | T1 for wiring (module itself is independent) | Yes as a module | Recommended | SMALL |
| T8 | Plan-level resume: reconcile stuck `RUNNING` steps, `run_goal` re-entry by plan id | §6 | T1 | No | Post-MVP-first (MVP limitation, disclose) | MEDIUM |
| T9 | Preflight/skip visibility: fail or warn loudly when Postgres is down instead of skipping 33 tests | §2 | none | Yes | Post-MVP process fix (cheap; worth doing early) | SMALL |

Deliberately not listed (post-MVP hardening, §11): sandbox, retries,
secrets, second provider, replanning.

## 10. Parallelism

- **One lane carries the MVP critical path: T2 -> T1 (+ T3 inside it) ->
  T4.** They all touch the same seam (`PlanRunner`'s contract with
  `driver_factory`, the composition root, and step context). Splitting them
  across two workers recreates the exact failure this review was asked to
  avoid.
- T6 changes `RuntimeDriver` failure policy and interacts with T2/T1
  behavior; keep it in the same lane, after T1.
- Genuinely independent: T5 (docs, director-owned), T9 (test hygiene), and
  T7 as a standalone module. T4 is bounded mostly by having a credential.
- If only one worker is available, the order is T2, T1+T3, T4; T5 whenever.

## 11. Final status (three separate assessments)

Measure used: "chain links" from §4.

**Core engine.** All 14 chain links exist as implemented, tested code;
recovery, persistence, contracts, provider abstraction, and permission
enforcement are real. Gaps inside the engine: no plan-level resume, no
cross-step context, denial halts a step. Strong, and I would not add engine
features before wiring it.

**MVP product.** 0 of 14 links are usable without writing new code
(1 missing outright, the rest lack a production composition). Estimated
remaining: T1, T2, T3, T4, T5 as required work, T6/T7 recommended. I am
not giving a percentage; the remaining work is few but concentrated, and
sizes differ by an order of magnitude between T1 and the rest.

**Production hardening.** Substantial and mostly untouched: sandbox/
container isolation (`SANDBOX_CONTRACT` still frozen/unimplemented); shell
policy is regex-based and self-described as evadable; secrets handling
beyond one pattern; provider retry/backoff/timeouts; rate/cost control for
free tiers; concurrency and observability; symlink handling not audited;
only one real provider ever exercised; plan-level resume; replanning.

## 12. What is exactly left before Neptune is "finished"

For a demonstrable MVP: **build the thing that runs it** (T1, with T2 and
T3), **run it once for real** (T4), and **make the documentation and ledger
tell the truth** (T5). Everything else in the engine is already there.
For "production-ready": a long list in §11 that the current architecture
does not block but nothing has started.

## 13. Process notes

- The two-lane split again produced work that composes only in theory: B-013
  (approval) and A-011 (execution) never met, which is why ASK has no
  driver-path test. The MVP-critical work above should be single-owner.
- `assignments.yaml` has no entries for several completed tasks (A-009,
  A-010, B-012, B-013, Reviews 005-007) because parallel rounds froze it;
  reconciliation was deferred and is still outstanding.
- I did not re-inspect the ADR index contents beyond confirming it exists;
  pending ADR decisions from Reviews 004-006 are recorded in those reviews.
