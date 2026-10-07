# DIRECTOR_REVIEW_008 — Final MVP Readiness Audit

Read-only audit of `main` @ `54c3c29` (identical to `origin/main` when checked).
No source, test, contract, README, ledger or ADR file was modified; the only repository change is this document.

**Provenance.**
- Everything marked *measured* or *probed* was run by me in this session, against the real repository and a real local Postgres.
- The repository tool connection dropped partway through the audit. After it returned I re-checked the items I had left open and updated this document; §13 says which findings changed as a result.
- I wrote the T1–T3 code (commit `9a5d643`) that this audit examines. I applied the same standard I would to anyone's code, but an independent reviewer should confirm FINDING-002 and FINDING-003, which concern my own work.

## 1. Executive result

**Answer to the core question: partly.** A real user can run `python -m neptune "<goal>"`, and the goal goes through the real production composition: planner → plan persisted → `PlanRunner` → `RuntimeDriver` → dynamic tool offering → permission/approval → real filesystem/shell tools → printed result. That chain is proven against real Postgres, real registry seeding, real tools and the real permission policy, **with the model faked**. It also works from a fresh clone (§3).

It has **never run with a real model** in its current form. The nearest evidence is a probe that reached Groq's API with a deliberately invalid key and got a genuine `401`. That proves the wiring up to the network boundary, not agent behaviour.

Separately, the result Neptune prints is **not always truthful** (FINDING-002): a shell command that exits non-zero is shown as `success`, and a step is "completed" whenever the model stops calling tools.

**Verdict: NOT YET MVP READY** (§15).

## 2. Actual end-user call graph

| Boundary | Actual code | Reachable by a user? | Exercised through this exact composition in tests? | Real provider? |
|---|---|---|---|---|
| User goal | `python -m neptune "<goal>" --workspace DIR` → `src/neptune/__main__.py` → `neptune.cli.main` | Yes, with `PYTHONPATH=src` | Yes (`tests/integration/cli/test_cli.py`, 8 tests) | n/a |
| Composition | `neptune.application.composition.build_plan_runner` | Yes | Yes | n/a |
| Registry | `load_registry_directory(06_REGISTRIES/data, …)` | Yes | Yes | n/a |
| Tools | `ReadFileTool`, `WriteFileTool`, `ListDirectoryTool`, `RunCommandTool` under one `WorkspaceBoundary` | Yes | Yes | n/a |
| Permission | `ToolExecutorService.execute` → `DefaultPermissionPolicy.evaluate` (default-on, not overridden) | Yes | Yes | n/a |
| Approval | `CliApprovalProvider` (`neptune/infrastructure/security/cli_approval.py`) passed to `ToolExecutorService` | Yes | Yes (scripted input) | n/a |
| Runtime | `driver_factory` in composition → `RuntimeDriver(context_provider=…)` | Yes | Yes | n/a |
| Model gateway | `_default_model_gateway_factory` → `ModelGatewayAdapter` → `ModelGatewayService` → `GroqAdapter` | Yes | **No.** Tests inject a fake via `model_gateway_factory` | Probed to HTTP 401 only |
| Tool offering | `ToolOfferingResolver.available_tools(["tool_use","terminal"])` + concrete-definition expansion | Yes | Yes | n/a |
| Executor → result | `ToolExecutorService` → `ToolPortAdapter` → observation | Yes | Yes | n/a |
| Step/plan result | `PlanRunner._run_step` → `PlanExecutor.complete_step/fail_step` | Yes | Yes | n/a |
| User-facing result | `neptune.cli.main` print loop, exit codes 0/1/2/3 | Yes | Yes | n/a |

No link in this chain exists only inside tests. The one link tests never take is the real model gateway (`_default_model_gateway_factory`).

## 3. Entry-point result

- **Command:** `PYTHONPATH=src python -m neptune "<goal>" --workspace DIR`.
- **Real graph:** yes. The real-composition probe seeded the DB from YAML, resolved a Groq model and made an HTTP request.
- **`PYTHONPATH=src` is required** (no installed package; `pytest.ini` sets `pythonpath = src` for tests only). It is documented in the docstring of `src/neptune/cli.py`. It is **not** documented in the README, which does not mention the CLI or `requirements.txt` at all (FINDING-005).
- **Fresh checkout: verified.** I cloned committed `main` into a temp directory, created a new venv, installed only `requirements.txt` (exit 0), and ran with `PYTHONPATH=src`:
  - `--help` printed usage;
  - without a key, exit 2 with the correct message;
  - with an invalid key, it seeded, routed, reached Groq and exited 3 with the genuine `401` text, creating no files.
  This ran against the same local Postgres container the README tells users to start (`docker compose up -d`). The clone and temp workspace were deleted afterwards.

## 4. Goal → Plan result

| Proof level | Status |
|---|---|
| Mock model | Yes: planner unit tests (14) and CLI tests. Malformed output, empty steps, duplicate ids, cycles and unknown references all fail without persisting. |
| Integration (real Postgres, real composition) | Yes. |
| Real provider | **None.** The only real-network evidence is the 401 probe. The ledger itself says "LIVE PROOF NOT OBTAINED" for A-010. |

Probed: with an invalid key, the CLI reported `could not produce a valid plan: … Groq authentication failed (401)`, executed nothing, and wrote no files. Planner errors do not become fake success. Minor: exit code 3 covers both "bad plan output" and "provider/auth failure" (FINDING-006).

## 5. Plan → Execution result

`PlanRunner.run_goal` → `PlanExecutor.select_next_step/start_step` → `driver_factory(task_id)` → `RuntimeDriver.execute_task` → tools. In the CLI path the `driver_factory` is the production one in `composition.py`, not a test helper. I found no direct-tool-call or permission-bypassing path: every tool call goes `AgentRuntime` → `ToolPortAdapter` → `ToolExecutorService`. The only mocked piece in the CLI tests is the model, and the test docstrings say so.

## 6. Dynamic tool result

The historical gap (catalog entry `filesystem` with no usable schema) is **closed in the production composition**. Probed against the real seeded registry: offerings `['filesystem', 'terminal']` expand to `read_file(path)`, `write_file(path, content)`, `list_directory(path)`, `run_command(command)`. All four have non-empty schemas. This depends on the caller passing `concrete_tool_definitions`; the composition root does. Offering is not an execution gate: `ToolExecutorService` will run any registered tool regardless of what was offered.

## 7. Permission / approval result

| Case | Through the full CLI composition? | Other evidence |
|---|---|---|
| ALLOW | Yes (file write/read, shell echo) | |
| DENY | Yes: no prompt shown, marker file never created, step FAILED, dependent SKIPPED | |
| ASK + approve | Yes: prompt shown with the command, real shell ran | |
| ASK + reject | Yes: shell never ran, step FAILED | |
| Approval channel failure (`ApprovalError`) | **No** | Code read in `executor.py`: returns `DENIED`. `CliApprovalProvider` EOF → `ApprovalError` is unit-tested. B-013 executor tests. |
| Unknown/garbage approval answer | **No** | Code read: any value `!= APPROVED` is denied |
| Provider raising a non-`ApprovalError` exception | No | Code read: not caught; propagates out of `run_goal` as a traceback. No success is reported. Post-MVP. |
| Tool executed after denial | Never observed | Marker-file tests |

ASK is reachable through the production composition and a human prompt exists, so "abstraction only" no longer applies.

**What is protected, precisely.**
- *File tools:* absolute paths, `..` traversal and symlink resolution are rejected (`WorkspaceBoundary`).
- *Shell:* only the starting directory is pinned. **Probed:** `echo escaped > ..\ESCAPED.txt` wrote a file outside the workspace, with no prompt, and the run reported success.
- *Policy:* three regex deny classes and three regex ask classes (remote-branch delete / production migration / secret export; package install / `git push` / network tools). Everything else is allowed by omission.
- *Not provided:* sandbox, process isolation, resource limits. That is post-MVP per the existing scope, but the user-facing help text overstates it (FINDING-003).

## 8. Failure semantics result

Probed through the real CLI composition with a scripted model, except where noted.

| Case | Can it be reported as success? | Evidence |
|---|---|---|
| Malformed plan output | No: exit 3, nothing runs | tested |
| Gateway error while planning | No: exit 3 with the underlying error text | probed (401) |
| Gateway error during a step | No: step FAILED (fixed in `9a5d643`; `RuntimeDriver` alone would call it completed) | tested |
| Plan validation failure | No | tested |
| Tool denied | No: FAILED, dependents SKIPPED | tested |
| Approval rejected | No | tested |
| Approval channel failure | No (denied) | code read |
| Filesystem tool error (e.g. missing file) | No, but the step ends at once and the model never sees the error | probed, FINDING-004 |
| Tool raises / times out in the executor | No: `ERROR`/`TIMEOUT` → step FAILED | code read |
| **Shell command exits non-zero or times out** | **Yes.** Returned as `SUCCESS`; CLI prints `tool run_command: success`; exit code not shown | probed (`exit 3` → `RESULT: all steps succeeded`, exit 0), FINDING-002 |
| **Model makes no tool call and claims success** | **Yes.** Step is COMPLETED | probed, FINDING-002 |

Root cause of the last two: a step succeeds when the model stops requesting tools and no tool call was an error. Nothing checks that the step's work happened. The last model message is printed, so a careful reader can see it, but the line `RESULT: all steps succeeded` overstates what was established.

## 9. Persistence / recovery result

Supported and tested: persistence of plans, steps, tasks, turns and checkpoints in Postgres; resuming an individual stopped task via `execute_until_stop` (A-011 test); cross-process tool-execution recovery (earlier tests).

Not implemented, by design, and correctly stated as such in README lines 21 and 87–89 (no overclaim found):
- goal-level or plan-level resume;
- reconciliation of a step left `RUNNING` by a crash;
- cross-step conversation history (only the goal text is passed, as background).

Verified in code this session: `PlanExecutor.select_next_step` returns only `PENDING` steps, and `start_step` raises `IllegalPlanTransition` for anything not `PENDING`, so a step left `RUNNING` is never picked up again. `PlanRunner` contains no resume logic (its only mention is a docstring line saying so). Resubmitting a goal creates a new goal id and a new plan and starts over. I found nothing implemented-but-broken. Not tested: any crash-and-restart of the CLI itself.

## 10. Live-provider evidence

| Class | Evidence |
|---|---|
| **A. Executed in this final state** | None. One probe (and the clean-clone run) made a real HTTPS request to Groq with an invalid key and received `401 Invalid API Key`. That shows seeding, routing and the HTTP adapter work up to authentication. It says nothing about model behaviour. `GROQ_API_KEY` is not set here. |
| **B. Executed earlier and recorded in the ledger** | A key was supplied 2026-08-15; B-003 records 3 live tests passing against a real Groq model; B-008 records a live call that found the original model retired; B-009 records "303 passed with GROQ_API_KEY present"; B-011 records successful real-Groq end-to-end runs including a file created by a real model. I read these records; I did not re-run them. They predate A-008…A-011, B-012/B-013 and the CLI, so they do not cover the current code path. |
| **C. Mocked only** | Goal→plan, plan execution, permission, ASK/approval, CLI. |
| **D. Skipped** | 9 tests, all `GROQ_API_KEY` (§11). |

The seeded model (`openai/gpt-oss-120b`) was last verified 2026-08-31 and the file records that the previous model had been retired by Groq. I did not re-check availability.

## 11. Skipped-test classification

Measured: **386 collected.**

| Run | Passed | Failed | Skipped |
|---|---|---|---|
| As found (Neptune Postgres stopped) | 336 | 0 | 50 |
| With `docker compose up -d` | 377 | 0 | 9 |

The as-found numbers match the brief exactly.

| Category | Count | Meaning | Blocks MVP? |
|---|---|---|---|
| Postgres not reachable | 41 (as found only) | Environment: container stopped. Skips every DB-backed proof, including the CLI and A-011 tests. | No, but a green run in this state proves far less than it appears to. README line 94 documents it. |
| `GROQ_API_KEY` not set | 9 (always) | Live tests: gateway, tool-call, B-009 loop, dynamic-tools loop, A-010 plan, A-011 execution, three Groq e2e. | **Yes, until T4 runs.** |
| Intentional / other | 0 | | |

There is **no live-gated test for the CLI itself**.

## 12. Documentation / state consistency (reported, not changed)

- README line 5 and line 58: "no user-facing entry point yet / a user cannot submit a goal today." **False on `main`.**
- README lines 74–79 ("Not built yet": CLI, goal-in-context, approval channel) and line 122 ("None of this exists in the repository yet"): **stale.** T1–T3 are built.
- README line 71: "the only production provider auto-rejects, so ASK currently behaves as deny": **stale.** `CliApprovalProvider` is wired in the CLI (auto-reject remains the executor's default when none is supplied).
- README has no run instructions: no CLI command, no `PYTHONPATH=src`, no `pip install -r requirements.txt`.
- README lines 83, 87–92 (unverified live paths, post-MVP limitations): accurate.
- `DEVELOPMENT_STATE/assignments.yaml`: last entry is `NEPTUNE-DIRECTOR-REVIEW-007`; **no entry for the T1–T3 work (`9a5d643`)**. A-009, A-010, A-011, B-012, B-013 do have entries.
- `workers.yaml`: A's `current_task` is null with a note asking the director to set it. Not a defect.
- `decisions.yaml`: no entries for the composition root, the goal-as-background requirement, or the provider-error→step-failure rule. An existing note (~line 1101) that only tests instantiate `ToolExecutorService` is now false.
- ADR index ends at ADR-046; four decisions are pending unnumbered, consistent with README line 124. Awaiting the director, not a defect.
- `cli.py` `--workspace` help overstates confinement (FINDING-003).

## 13. Findings

### FINDING-001 — No real-model evidence for the current code
- **Claim:** Goal→plan, plan execution, permission and ASK with a real model have never run; the MVP evidence gate (T4) is open.
- **Evidence:** `GROQ_API_KEY` unset; 9 live tests skipped; 401 probe only; no live test exists for the CLI; ledger says "LIVE PROOF NOT OBTAINED" for A-010.
- **Classification:** UNPROVEN (ENVIRONMENT LIMITATION). It gates the verdict.
- **Impact:** Whether a free-tier model produces valid plan JSON and completes multi-step plans is unknown. Model-id drift is a known past failure.
- **Required action:** one real run of the CLI with a key; record the transcript whether it succeeds or fails.

### FINDING-002 — The printed result can report failure as success
- **Evidence:** probe A (`exit 3` → `tool run_command: success`, `RESULT: all steps succeeded`, exit 0); probe B (no tool call → completed). Code: `shell_tool.py` returns non-zero exit and timeout as normal output; `ToolPortAdapter` maps `SUCCESS` → `status: "ok"`; `RuntimeDriver.should_complete` is "no tool calls".
- **Classification:** MVP GAP. The system is not required to verify the model's work, but it must not label a failed command `success`.
- **Impact:** A user running tests, builds or scripts can be told everything succeeded when a command failed.
- **Required action:** display-only: show `exit_code` and `timed_out` per tool call, and word the RESULT line as "steps finished" rather than "succeeded". No verification feature is implied.

### FINDING-003 — `--workspace` help overstates what the shell is confined to
- **Evidence:** help text says "directory the agent may read/write/run commands in"; probe wrote outside the workspace with no prompt. File tools are confined; the shell is not.
- **Classification:** DOCUMENTATION GAP (the lack of isolation itself is POST-MVP and already stated in README line 90).
- **Impact:** A user may believe the agent cannot touch files outside the directory they pass.
- **Required action:** correct the help text and add the limitation to the README.

### FINDING-004 — Any tool error ends the step; the model never sees it
- **Evidence:** probe C: a `read_file` on a missing file failed the step although the scripted model would have continued. `RuntimeDriver.tool_failed` stops on any `status == "error"`. Review 007 listed this as T6, "recommended".
- **Classification:** POST-MVP as currently scoped; flagged because models commonly probe for files, so it is a likely cause of failures in the first real run.
- **Impact:** Lower success rate on real goals. Reported truthfully as failed.
- **Required action:** none required to freeze. Director decision after FINDING-001 shows how often it occurs.

### FINDING-005 — README, ledger and decisions are stale after T1–T3
- **Evidence:** §12.
- **Classification:** DOCUMENTATION GAP.
- **Impact:** The README tells a reader the product cannot be run, and gives no way to run it.
- **Required action:** update README current state and add the run instructions (install, `docker compose up -d`, `PYTHONPATH=src`, command); add the missing ledger and decision entries.

### FINDING-006 — Exit code 3 conflates plan-output failure with provider failure
- **Classification:** POST-MVP (message text is truthful). **Required action:** none.

### FINDING-007 — A green suite without Postgres skips most real-tool proofs
- **Evidence:** 336 passed / 50 skipped with 0 failures, versus 377 / 9 with Postgres.
- **Classification:** ENVIRONMENT LIMITATION (documented in README line 94).
- **Required action:** none for MVP; always report suite results with Postgres up.

### FINDING-008 — Fresh-checkout run (closed)
- **Claim (raised earlier in this audit):** a clean checkout might not run the CLI.
- **Evidence:** clean clone of `main`, new venv, `pip install -r requirements.txt` succeeded, CLI ran as described in §3, through to the real Groq 401.
- **Classification:** NON-ISSUE. The remaining gap is that the README does not say how to do it (FINDING-005).
- **Required action:** none beyond FINDING-005.

## 14. MVP-required completion matrix

Source of scope: Review 007 §9 and the final MVP brief (T1–T4).

**Required and complete**
- Entry point and composition root (T1), exercised end-to-end with a fake model, and working from a clean clone.
- Original goal reaches every step (T2), tested.
- Human approval channel (T3); ALLOW/DENY/ASK-approve/ASK-reject proven through the CLI composition.
- Dynamic tool offering with real schemas.
- Plan generation, validation and persistence; plan execution through `RuntimeDriver`.
- Provider errors do not become step success.

**Required but unproven**
- T4: a real-model end-to-end run (FINDING-001).
- A truthful user-facing result (FINDING-002).
- Documentation that matches the product (FINDING-005, FINDING-003).

**Not MVP / post-MVP**
- Goal-level resume and RUNNING-step reconciliation; cross-step conversation history; sandbox/isolation; tool errors fed back to the model (FINDING-004); retries/backoff; second provider; replanning; MCP; multi-agent.

## 15. Final verdict

**NOT YET MVP READY**

The architecture does not prevent the MVP. The chain exists, is user-reachable from a clean checkout, and is proven with a fake model. It is not freezable because the evidence gate was never run, the printed result can mislabel a failed command as success, and the documentation says the product cannot be run.

## 16. Smallest remaining closure list

1. **Run T4:** one CLI run with a real `GROQ_API_KEY` of the `hello.txt` goal; record the outcome either way. Needs a key.
2. **Fix FINDING-002 (display only):** show `exit_code`/`timed_out` per tool call; change the RESULT wording.
3. **Fix FINDING-003:** correct the `--workspace` help text.
4. **Reconcile docs (FINDING-005):** README current state and run instructions; ledger entry for `9a5d643`; decisions entries.

After item 1, the director should decide whether FINDING-004 gets fixed before or after freeze, based on what the real run shows.

## Appendix — what this audit left behind

- Scratch probe scripts in `%TEMP%` (`probe_real_path.py`, `probe_failure_semantics.py`, `probe_shell_escape.py`, `probe_offering.py`); temp workspaces and the clean clone were deleted.
- Probes wrote rows to Neptune's Postgres, as the tests do. I started the `neptune-postgres` container and left it running.
- `git status` was clean after all test and probe runs (checked after the connection returned).
