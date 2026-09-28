# DIRECTOR-REVIEW-006 — A-011 Goal-to-Execution Integration

## 1. Status

**A-011 complete.** GoalPlanner's output now reaches the existing
execution architecture (PlanExecutor -> RuntimeDriver -> AgentRuntime ->
dynamic tool offering -> permission layer -> ToolExecutor -> real tool
-> observation -> completion/checkpoint) through one new, small
sequencer, `PlanRunner`. No second execution architecture was created.

Full suite: 349 collected, 340 passed, 0 failed, 9 skipped (see §11).

## 2. Exact integration seam

`GoalPlanner.plan_goal()` returned a persisted `Plan`, and nothing
consumed it. `PlanExecutor` tracked step status but never ran anything.
`RuntimeDriver.execute_task()` ran tasks but never knew about a `Plan`.

The seam is: **for each step `PlanExecutor.select_next_step()` returns,
run that step as one `RuntimeDriver.execute_task()` call, then feed the
real `DriverOutcome` back into `PlanExecutor.complete_step()` /
`fail_step()`.** That is all `PlanRunner` does.

## 3. Call graph before

```text
GoalPlanner.plan_goal(goal) -> Plan (persisted)          [dead end]
PlanExecutor.select/start/complete/fail_step             [called only by hand/tests, no real work behind it]
RuntimeDriver.execute_task(task_id, requirements=...)    [no Plan behind it]
```

Verified by search in Review 005: no file wired `PlanExecutor` to
`AgentRuntime`/`RuntimeDriver`.

## 4. Call graph after

```text
PlanRunner.run_goal(goal)
  -> GoalPlanner.plan_goal(goal)               (unchanged; validates, persists)
  -> loop:
       PlanExecutor.select_next_step(plan)     (unchanged)
       PlanExecutor.start_step(plan, id)       (unchanged)
       driver = driver_factory(task_id)        (caller-injected)
       RuntimeDriver.execute_task(task_id, requirements=[title, description?],
                                  constraints={"capability": ...}?)   (unchanged)
         -> context_provider -> ToolOfferingResolver (request-time)
         -> AgentRuntime.run_turn -> ModelGateway
         -> ToolPortAdapter -> ToolExecutorService
              -> DefaultPermissionPolicy (before dispatch)
              -> real tool
         -> observation -> next turn -> completion/checkpoint
       COMPLETED          -> PlanExecutor.complete_step
       any other outcome  -> PlanExecutor.fail_step (cascade-skips dependents)
```

## 5. Files changed

- `src/core/planning/plan_runner.py` (new): `PlanRunner`, `PlanRunResult`,
  `StepExecutionResult`, `DriverFactory`.
- `tests/unit/planning/test_plan_runner.py` (new, 4 tests).
- `tests/integration/planning/test_goal_to_execution.py` (new, 4 tests, 1 live-gated).
- `DEVELOPMENT_STATE/assignments.yaml`: one append-only entry for A-011.
- `DIRECTOR_REVIEW_006.md` (this file).

No existing source file was modified.

## 6. Why this integration point was selected

- `RuntimeDriver.execute_task()` already turns a requirements list into
  a full task/session/turn/checkpoint lifecycle, and is documented as
  the runtime authority. Reusing it per step means no bypass.
- `PlanExecutor` already owns step ordering, dependency gating, failure
  cascade, and persistence. Driving its existing transitions from real
  outcomes reuses all of that.
- Adapters (`ModelGatewayAdapter`, `ToolPortAdapter`) are documented as
  constructed fresh per task, and `AgentRuntime` is bound to them. So
  one step = one fresh driver. Building it inside Core would require
  importing infrastructure, so it is injected as `driver_factory`, the
  same inject-a-callable pattern A-009 used for `context_provider`.
  `PlanRunner` imports only `core.*` and stdlib; the static
  provider-independence test covers it and passes.

## 7. Goal -> Plan -> Execution proof

`test_real_goal_flows_through_plan_runner_to_real_execution`: a real
`GoalPlanner` produces a 2-step plan (`write` -> `read`); each step runs
through a real `RuntimeDriver`; `hello.txt` really exists on disk with
content `hello`; both steps and the persisted plan end `COMPLETED`;
every step's task is `completed` with a checkpoint. The canonical
registry and `ToolOfferingResolver` supplied `filesystem` in each
step's `model_request["available_tools"]`.

Only the model is faked (`FakeModelGateway`, one shared scripted
instance consumed by the planner call and every step's turns).

## 8. Permission proof

`test_permission_denial_blocks_step_before_the_shell_never_runs`: the
real `ToolExecutorService`, constructed with no policy override (so
B-012's default-on `DefaultPermissionPolicy`), receives a scripted
`git push origin --delete x; echo ran > marker` call. Results: marker
file absent (command never ran); observation `status == "error"`,
`outcome == "denied"`; driver outcome `STOPPED_TOOL_FAILURE`; step
`FAILED`; dependent step `SKIPPED`; `all_succeeded` is False.

This closes the gap Review 005 named: B-012's denial is now proven
through the full driver path, not only via direct
`ToolExecutorService.execute()` calls.

## 9. Observation / completion proof

Turn 1 of each step carries a real tool observation (`status: ok`);
turn 2 receives it and finishes with no tool calls; `RuntimeDriver`
completes the task and checkpoints. Covered by the integration test
above (per-step `task.status == completed`, `last_checkpoint` present).

## 10. Recovery result

`test_plan_step_task_is_resumable_like_any_other_runtime_task`: a
plan-step-shaped task is stopped after 1 turn (`STOPPED_MAX_TURNS`),
then a freshly built driver resumes via `execute_until_stop()` and
completes it; the resumed write really lands on disk.

Scope limit, stated plainly: this proves a plan-step *task* is resumable
using the same mechanism as every other task. It does **not** prove
resumption of the *PlanRunner loop itself* (e.g. crash between steps,
then re-enter `run_goal`). `PlanRunner` has no resume entry point and
treats a non-`COMPLETED` step as failed. Plan state is persisted, so the
data needed exists, but that behavior is not built or tested. Existing
two-process recovery tests are unchanged and pass.

## 11. Test results

```text
collected: 349    passed: 340    failed: 0    skipped: 9
```

Baseline before this task was 341 collected (333 passed, 8 skipped).
New: 8 tests (4 unit, 4 integration incl. 1 live-gated). The 9 skips are
the 8 pre-existing `GROQ_API_KEY` guards plus the new live test. Postgres
was up via `docker compose`. Existing B-011, A-009, B-012, A-010 and
recovery tests all still pass.

## 12. Live-test result

**Not run.** `GROQ_API_KEY` is not set in this environment (confirmed).
`test_real_goal_flows_through_plan_runner_to_real_execution_live_groq`
exists, collects, and skips with an explicit reason. It was also never
executed against a real key, so its assertions are unverified beyond
collection; treat it as wired but unproven. No live result is claimed.

## 13. Architectural changes

One additive Core class. It adds a composition pattern (one plan step =
one fresh task, driver injected by factory). It changes no contract,
type, or behavior of any existing component. No new ADR created.
Proposed for the director to decide (no number assigned): whether "Plan
steps execute as independent RuntimeDriver tasks via an injected driver
factory" merits an ADR. It is a real design choice with a notable
consequence (steps do not share task/session context), so I lean toward
recording it.

## 14. Out-of-scope confirmation

Not modified: planning model, `PlanExecutor`, `GoalPlanner`,
`RuntimeDriver`, `AgentRuntime`, `ModelGateway`, permission policy,
tools, providers, registry. No sandbox, browser/MCP, retries,
multi-agent, or hardening added. Shared state: only an append-only
`assignments.yaml` entry for A-011. `decisions.yaml`, `workers.yaml`,
and `00_ADR_INDEX.md` untouched. Note the file still lacks entries for
A-009, A-010, B-012 and Review 005; I did not backfill them (out of
scope), so that reconciliation remains outstanding.

## 15. Known limitations

- **Steps are context-isolated.** Each step is a separate task; the
  model in step 2 does not see step 1's turns or observations, only its
  own title/description. In the tests this works because the filesystem
  carries state. For real plans, information not written to disk will be
  lost between steps. This is the most important limitation and the
  natural next gap.
- **No product entry point.** `PlanRunner` is still only reachable from
  tests; Review 005's "no CLI/main" finding is unchanged.
- **Denial still halts its step** (`tool_failed()` cannot tell denial
  from crash); no replanning after failure.
- **Sequential only**, and `max_turns` exhaustion counts as failure.
- **Live path unverified** (§12).
- **Loop-level resume** unbuilt (§10).

## 16. Next recommended step

Closing the context-isolation gap is the most valuable follow-up: pass
prior completed steps' outcomes into the next step's requirements or
context (via existing `requirements`/`constraints` or the
`context_provider` seam), so multi-step plans can carry information that
is not on disk. Separately, a single real entry point would make this
path reachable outside tests. Both are the director's call; I have not
started either.
