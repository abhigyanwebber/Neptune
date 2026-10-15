# DIRECTOR_REVIEW_009 — MVP Closure Report

Closure pass on `worker/claude-a` (starting from `01c8ae0`, which is `main` at `54c3c29` plus Review 008).
Nothing was merged.

**Verdict: NOT YET MVP READY.** The one remaining item is a recorded run of the CLI with a real `GROQ_API_KEY`. No key exists in this environment, so it was not performed (§4).

Notes on inputs:
- `DIRECTOR_REVIEW_008B.md` (lane B's audit) is not in the repository or on any remote. I worked from the closure brief's description of it. Its `%GROQ_API_KEY%` finding I re-derived independently (§3).
- Neptune's Postgres container exited twice during this pass (Docker Desktop restarts). Every result below was taken after confirming the database answered a query, not just that the container was listed.

## 1. Corrections made

| # | Change | Where |
|---|---|---|
| 1 | A failed command is now a failed tool execution (timeout -> `TIMEOUT`, non-zero exit -> `ERROR`, output kept) | `src/neptune/infrastructure/tools/executor.py` |
| 2 | The export-secret deny rule now matches real variable names | `src/neptune/infrastructure/security/permission_policy.py` |
| 3 | Final CLI line reworded; `--workspace` help corrected (shell is not confined) | `src/neptune/cli.py` |
| 4 | Two tests that asserted success for a command that actually failed were corrected | `tests/integration/security/test_ask_approval.py`, `tests/integration/cli/test_cli.py` |
| 5 | README, ledger, decisions, workers reconciled | see §6 |
| 6 | 23 new tests | see §5 |

Items 3 and 4 go slightly beyond the literal list. 3 is a truthfulness/documentation fix from the same audits; 4 was forced by item 1 (below). Say if you want either reverted.

## 2. False-success root cause

The path, as traced in code and reproduced in Reviews 008 and 008B:

```text
RunCommandTool.execute        returns {"exit_code": 3, "timed_out": False, ...} as a normal result (by B-010 design)
ToolExecutorService.execute   labelled any returned result ToolOutcome.SUCCESS
ToolPortAdapter               SUCCESS -> observation status "ok"
RuntimeDriver.tool_failed     stops only on status == "error"  -> loop continued
PlanRunner                    step COMPLETED when the model stopped asking for tools
CLI                           "all steps succeeded", exit 0
```

**Fix at the layer that decides the outcome**, not the printed string. `ToolExecutorService` now inspects the tool's result: `timed_out: true` becomes `TIMEOUT`, a non-zero integer `exit_code` becomes `ERROR` (a bool is not an exit code). The output stays attached, so stdout, stderr and the exit code remain in the observation and the persisted turn. The tool's own contract and unit tests are untouched. Filesystem tools have neither field and are unaffected.

Propagation after the fix (each link asserted by a test): `ToolResult.outcome=ERROR` -> observation `status:"error"` -> `RuntimeDriver` stops (`STOPPED_TOOL_FAILURE`) -> `PlanRunner` fails the step and skips dependents -> CLI prints `[failed]`, `tool run_command: error (command exited with code 3)` and `RESULT: not all steps completed`, exit 1.

**A fact about my own earlier tests.** The ASK-approve tests (B-013's, and the CLI one I wrote) used `curl --version; echo ran > marker`. On this Windows shell `;` is not a separator, so that command really exits `2` while the marker file still appears. Both tests passed *because* failure was invisible, which is the exact bug being fixed. They now use `&&`. The deny/reject cases that never execute were left alone.

**A consequence you should decide on, not hidden:** any failing command now ends its step, including one a model would have fixed and re-run (a failing test run, `grep` with no match). `RuntimeDriver` stops on any error observation, so the model never gets to react. This matches the instruction (failed tool != successful step) and the existing behaviour for every other tool error, but it limits iterative coding workflows. Feeding errors back to the model is the deferred "T6" item; I did not build it.

**Not fixed, by design:** a model that makes *no* tool call and claims success is still recorded as a completed step. That is not a tool failure. The final line now says "completed with no tool errors" rather than "succeeded", and the README states the limitation.

## 3. Permission / approval result

**`echo %GROQ_API_KEY%`: a genuine defect inside the existing heuristic, fixed minimally.**
- *Should it be denied?* Yes: `07_SECURITY/02_PERMISSION_MODEL.md` lists "export secret" as `deny`, and the rule's own pattern targets `echo`/`printenv`/`cat` with `API_KEY`/`TOKEN`/etc.
- *Why it passed:* the pattern put `\b` before the secret term. `_` is a word character, so there is no boundary inside `GROQ_API_KEY`, `GITHUB_TOKEN`, `DB_PASSWORD` or `AWS_SECRET_ACCESS_KEY`. The rule effectively only caught a bare `echo TOKEN`. This is not obfuscation; the plain form failed.
- *Fix:* the term must not be preceded or followed by a letter or digit (`_` counts as a separator). One regex changed, no new mechanism.
- *Tests (15):* denied: `%GROQ_API_KEY%`, `$GROQ_API_KEY`, `${GROQ_API_KEY}`, `$env:GROQ_API_KEY`, `printenv GITHUB_TOKEN`, `%DB_PASSWORD%`, `$AWS_SECRET_ACCESS_KEY` and the two bare forms; allowed: `cat tokenizer.py`, `cat passwords.txt`, `echo secretary`, `echo hello`, `cat README.md`, `pytest -q`.
- *Still a heuristic:* it does not catch `set`, `env`, bare `printenv`, or an interpreter one-liner reading the environment. The contract documents this; I did not broaden it.

**Approval and denial through the production composition** (real Postgres, real registry, real tools, real policy, model faked): ALLOW, DENY (no prompt, marker file absent), ASK+approve (prompt shown, command really runs), ASK+reject (command never runs). The deny and reject tests now also assert the CLI never prints the success line. Approval-channel failure (`ApprovalError` -> denied) and unknown answers (anything but `APPROVED` -> denied) are covered by executor-level tests and code reading, not by a CLI-composition test. A provider raising some *other* exception propagates as an exception (recorded in `B-DEC-034`); no success is reported.

## 4. Current live-provider result

**Not performed.** `GROQ_API_KEY` is not set at process, user or machine level; there is no `.env` (only `.env.example`). I did not look for a key anywhere else and did not use one. Nothing is claimed.

What I could establish without a key:
- With a deliberately invalid key, the unmodified `python -m neptune` (final code) seeds the registry from YAML, routes to Groq, makes a real HTTPS request and receives a genuine `401 Invalid API Key`; it reports that truthfully, creates no files, exits 3. This proves wiring up to authentication. **It says nothing about model behaviour.**
- Groq's own deprecation page, and several secondary write-ups, list `openai/gpt-oss-120b` (the seeded model) as a current production model and as the named replacement for several retired ones. That is documentation, not a run.

To close the gate (one command, with a key, in a throwaway directory):
```text
$env:GROQ_API_KEY = "<key>"; $env:PYTHONPATH = "src"; docker compose up -d
python -m neptune "Create a file named hello.txt containing hello, then read it and verify its contents." --workspace <empty dir>
```
Record the whole transcript whether it passes or fails. A failure there (invalid plan JSON, a model that probes for missing files and trips the stop-on-error rule) is useful evidence, not a defect in this report.

Evidence classes, kept separate:

| Class | What exists |
|---|---|
| MOCK TEST | Planner, PlanRunner, permission policy, approval provider, failure semantics (unit) |
| INTEGRATION TEST | CLI through the real composition: real Postgres, real registry seeding, real tools, real permission policy, real approval provider; **model faked** |
| HISTORICAL LIVE TEST | Ledger records of real Groq runs for B-003, B-008, B-009, B-011. I read the records; I did not re-run them. They predate the planner, PlanRunner and CLI. |
| CURRENT LIVE TEST | **None.** (A 401 probe only.) |

## 5. Full regression result

With Postgres confirmed reachable (a query returned), final tree:

```text
collected: 409    passed: 400    failed: 0    skipped: 9
```
Previous: 386 collected / 377 passed. New: 23 tests (15 permission-policy cases, 5 command-failure semantics, 3 CLI).

The 9 skips are all `GROQ_API_KEY` guards: live gateway, live tool-call, B-009 loop, B-011 dynamic-tools loop, A-010 plan, A-011 execution, and three Groq e2e. They are not failures and are not counted as live proof. With Postgres *down* the same suite reports 0 failures but silently skips 41 more (documented in the README). I saw that happen twice during this pass; it is why I verified the database before each result.

## 6. Documentation reconciliation

- **README:** status line, current-state paragraph, permission bullet, the "Not built yet" block (now "Built for the MVP path"), "Not verified", known limitations (any tool error ends a step; shell not confined; "completed" is not "verified"), test counts, repository guide, next-milestone paragraph. A new **Running Neptune** section gives install, `docker compose up -d`, key, `PYTHONPATH=src` and the command, exit codes, and the two caveats. A search confirms the stale phrases ("no user-facing entry point", "None of this exists", "ASK currently behaves as deny") are gone.
- **assignments.yaml:** entries added for the T1-T3 work (`9a5d643`), Review 008 (`01c8ae0`) and this pass. Entries for A-009, A-010, A-011, B-012, B-013 already existed.
- **decisions.yaml:** `ADR-A-017/018/019` (ledger ids, not ADR numbers) record the composition root and goal context, the failed-command rule, and the secret-rule fix. The old `B-DEC-033` statement that only tests instantiate `ToolExecutorService` is left as written (true when recorded); `ADR-A-017` supersedes it explicitly. Title-only ADR proposals are unnumbered and unapproved.
- **workers.yaml:** A's notes extended; `current_task` stays null.
- All three YAML files parse. No ADR index change, no ADR created.

## 7. Remaining limitations (known, not fixed)

Out of scope for this closure:
- Any tool error ends its step and is not shown to the model, so a failing command cannot be retried within the step (see §2).
- A step with no tool call counts as completed; nothing verifies the work was done.
- Shell commands start in the workspace but are not confined; the rules are regex heuristics.
- No sandbox, no goal-level resume (a crashed `RUNNING` step is never picked up), no cross-step conversation memory, no retries.

Found during this pass, **not fixed** (not on the closure list):
- With Postgres down, the CLI prints a raw traceback and exits **1**, the same code as "not all steps completed".
- Exit code 3 covers both "bad plan output" and "provider/auth failure".
- A non-`ApprovalError` exception from an approval provider propagates as a traceback.

## 8. MVP acceptance matrix

| Requirement | Status | Evidence level |
|---|---|---|
| User can submit a goal (CLI, clean checkout) | Done | Clean-clone install and run verified in Review 008; real path to a Groq 401 re-verified here |
| Goal reaches every step | Done | Integration |
| Plan generated, validated, persisted | Done | Mock + integration |
| Steps run through RuntimeDriver with dynamic tool offering | Done | Integration (real schemas verified) |
| Permission ALLOW / DENY | Done | Integration |
| Human approval (ASK approve / reject) | Done | Integration |
| Failed tool/command is not reported as success | **Done this pass** | Integration + unit |
| Denial / rejection not reported as success | Done | Integration |
| Secret-printing commands denied | **Done this pass** | Unit |
| Documentation matches the repository | **Done this pass** | Search + review |
| Full regression green with the database up | Done | 400 / 0 / 9 |
| **Real-model end-to-end run** | **NOT DONE** | **No key available** |

## 9. Final verdict

**NOT YET MVP READY**

**Exact remaining blocker:** a single recorded run of `python -m neptune` with a real `GROQ_API_KEY`. Everything the MVP contract requires of the code and documentation is in place and tested with the model faked; what no one has ever observed is a real model producing a valid plan, choosing tools and completing steps through *this* system. It cannot be closed from within this environment because it needs a credential I do not have, and fabricating or inferring it would defeat its purpose.

Once that run is recorded (pass or fail), the verdict can be revisited. If it fails because the model's first failed `read_file` or failing command ends a step, that is the deferred stop-on-error limitation (§2, §7), and whether to address it before freezing is the director's call; it is not part of this closure.


---

## Addendum (2026-10-13): live acceptance run and release cleanup

Sections 1-9 above are left as written. They describe the repository at commit `96237b1`, where the verdict was NOT YET MVP READY because no real-model run existed. This addendum records what happened afterwards; it does not rewrite those findings.

**The blocker named in section 9 is closed.** On 2026-10-11, at `96237b1`, the CLI was run against the real Groq API (`openai/gpt-oss-120b`) with the goal `Create a file named hello.txt containing hello, then read it and verify its contents.`:
- the model produced a valid 2-step plan (`write_file` then `read_file`, with a dependency), persisted and ended `completed`; each step's stored request contained the original goal;
- the real tools ran: `write_file` wrote 5 bytes, `list_directory` returned `hello.txt`, `read_file` returned `hello`; the file on disk was exactly `b'hello'`;
- the CLI exited 0 with `all steps completed with no tool errors`. This was verified from the persisted plan, turns and tool-call records and the file, not from the CLI text.
- A second real-model run asked for a failing command. The model sent `sh -c 'exit 3'`, which genuinely failed on Windows (`sh` is not recognized, exit code 1). The observation was `status: error` with the exit code and stderr preserved, the step was `failed`, its dependent `skipped`, the CLI printed `not all steps completed` and exited 1. A failed command was not reported as success.
- Full suite at that point, with the key and Postgres up: 409 passed, 0 failed, 0 skipped (the nine live tests executed).
This is one goal on one model, not a reliability measurement.

**Release cleanup (working-tree changes, see ledger `NEPTUNE-RELEASE-CLEANUP`):**
1. The A-010 and A-011 live tests now seed the canonical registry themselves. Before, they failed on an empty database with `no candidate satisfies requirements` and passed only because the CLI tests seeded it first in suite order.
2. The A-011 live test now asserts real outcomes (every step `COMPLETED`, `hello.txt` exactly `hello`, a successful `write_file`, a `read_file` returning `hello`, the first response from the real provider). Strengthening it exposed a defect in the test itself: its adapter was built without `concrete_tool_definitions`, so the model had no tool schemas, answered in prose, and claimed a verification it never performed; both steps were recorded completed with an empty workspace. The earlier weak assertions could not see this. The test now passes the real tool definitions.
3. `test_registry_population_recovery` now accepts `registry.provider.registered` or `registry.provider.updated`. Cause confirmed in the implementation: `register()` emits `registered`, `update()` emits `updated`, and the loader upserts, so loading into a registry another process already populated (the CLI tests) emits `updated`. The recovery checks are unchanged. No audit events were added to CLI startup; the loader upserts every entry, so that would add about 30 events to every run.
4. The `run_command` description now names the shell (`cmd.exe` on Windows, `/bin/sh` elsewhere). Description text only; execution, boundaries and policy are unchanged. In a small live comparison on one goal the unmodified description led the model to send `sh -c "exit 3"` in 2 of 3 runs, and the new wording led it to send plain `exit 3` in 3 of 3. That is suggestive, not proof.

**Results after cleanup:** on an empty database (verified 0 tables before), full suite without a key: 412 collected, 403 passed, 0 failed, 9 skipped (all `GROQ_API_KEY`); with a key: 412 passed, 0 skipped. Each modified test was also run alone on an empty database, and both live tests in both orders.

**Still true, not fixed:** three older live tests (B-008, B-009, B-011) fail when run alone on an empty database for the same seeding reason and pass only in suite order; any tool error ends its step; the shell is not confined to the workspace; "completed" is not "verified"; only Windows has been run; the CLI prints a traceback if Postgres is down. `requirements.txt` was not changed: `pytest>=8,<9` resolves to 8.4.2 and the suite passed under it at `96237b1`; a locally installed pytest 9.1.1 also passes, so that is environment drift.
