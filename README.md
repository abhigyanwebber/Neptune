# Neptune

**A reusable, project-agnostic agent infrastructure — a provider-agnostic, self-hostable, Claude-Code-like execution environment.**

Specification version: 0.7.1 · Phase: implementation (post-architecture-freeze) · Status: MVP path implemented (goal -> plan -> execution through a CLI) and verified end to end with a real model on one goal (see Running Neptune)

## What is Neptune?

Neptune is infrastructure for running AI agents in production, without betting the whole system on any single model provider, framework, or paid tier.

Most agent projects hard-wire themselves to one LLM API and one execution harness. When that provider changes pricing, rate-limits, or deprecates a model, the project breaks. Neptune's answer is to treat models, tools, and resources as swappable components behind stable contracts, so the agent runtime keeps working even as the providers underneath it change.

Concretely, Neptune is a set of layered, contract-driven components — task/session/turn state, a model gateway, a tool execution boundary, a registry of providers and capabilities, and a recovery-capable runtime — designed to be reused across future projects rather than rebuilt per-project.

## Why Neptune?

- **Claude-Code-like production workflow** — a durable agent loop (goal → plan → model → tool → observation → next turn) rather than a one-shot script.
- **Provider/model freedom** — providers are adapters behind a gateway contract; no provider name is hard-coded into core logic.
- **Cost control** — built free/cheap-first, with paid or rate-limited resources treated as optional burst capacity, not a foundation.
- **Reusable infrastructure** — the runtime, registries, and contracts are meant to outlive any single project built on top of them.
- **Durable execution and recovery** — state (tasks, turns, checkpoints, events, plans) is persisted so an individual task can resume in a fresh process. Resuming a whole multi-step goal is not implemented yet (see Current State).

## How It Works

```text
Goal
  ↓
Planning
  ↓
Capability / Provider Resolution
  ↓
Runtime
  ↓
Model Gateway
  ↓
LLM
  ↓
Tool Execution
  ↓
Observation
  ↓
Next Turn / Completion
  ↓
Checkpoint / Recovery
```

- **Planning** (`core/planning`) turns a goal into an ordered, validated plan: `GoalPlanner` asks the model for structured steps and `PlanExecutor` tracks step status. `PlanRunner` executes a plan by running each step as its own runtime task; steps do not share turns or observations. The original goal text is included in every step's context as background.
- **Resolution** picks concrete capabilities, providers, and resources for a step from the registries (`core/resolution`).
- **Runtime** (`core/runtime`) drives a session turn-by-turn: assemble context, request a model turn, execute any requested tool calls, record the observation, decide whether to continue or complete.
- **Model Gateway** normalizes requests/responses across providers behind `MODEL_CONTRACT`/`PROVIDER_CONTRACT`/`ROUTER_CONTRACT`; the first live adapter is Groq.
- **Tool offering** — `ToolOfferingResolver` turns the canonical tool registry into the tool definitions sent with each model request, and `RuntimeDriver` can supply per-turn context through an optional `context_provider`.
- **Tool Execution** runs tool calls under a boundary that enforces timeouts and output-size limits (`TOOL_CONTRACT`). Before a tool runs, `ToolExecutorService` evaluates a permission policy: a call is allowed, denied, or, for `ask`-classified actions, sent to an `ApprovalProvider`. A denied or unapproved call never reaches the tool. A command that exits non-zero or times out is a failed execution, not a success.
- **Observation** feeds tool results back to the model as deterministic, replayable messages (ADR-043).
- **Checkpoint / Recovery** persists state to Postgres so a run can resume in a fresh process after a stop or crash.

## Current State

Neptune can be run: `python -m neptune "<goal>" --workspace DIR` plans the goal, runs each step through the runtime with real filesystem and shell tools, enforces the permission policy, and asks you at the terminal before any `ask`-classified action (see **Running Neptune**). This path is tested end to end with a **faked model** against real Postgres, tools and permission policy. It has also been run once end to end with a real model (see **Verified live run**): that is one goal on one model, not a reliability measurement. Closure report: `DIRECTOR_REVIEW_009.md` (with a dated addendum).

**Implemented and tested:**

- Core domain + persistence: Task/Agent/Session/Turn/Event/Checkpoint over Postgres, with a process-boundary recovery test.
- Registries: capability, provider, resource, and tool catalogs, with a YAML loader, JSON snapshot exporter, and audit trail. Production code reads the canonical registry.
- Resolution layer: capability → provider/resource selection and dependency expansion, independent of execution.
- Planning: `Goal`/`Plan`/`PlanStep` contracts and `PlanExecutor`; `GoalPlanner` (goal → validated, persisted plan through the model gateway); and `PlanRunner`, which connects planning to execution by running each plan step as its own `RuntimeDriver` task.
- Model Gateway: `MODEL_CONTRACT`/`PROVIDER_CONTRACT`/`ROUTER_CONTRACT` implemented and wired into `AgentRuntime`, with a live Groq adapter validated against the real API.
- Dynamic tool offering: `ToolOfferingResolver` offers registry-backed tools per request, and `RuntimeDriver` accepts an optional per-turn `context_provider`.
- Tools: `ReadFileTool`, `WriteFileTool`, `ListDirectoryTool` and `RunCommandTool` (plus `EchoTool`), with file access confined to the workspace by `WorkspaceBoundary`. Real coding-agent tool use was validated against a live model.
- Tool execution boundary: timeout and output-size enforcement; `ToolPortAdapter` bridges the Runtime's `ToolPort` contract to the real `ToolExecutor` (ADR-044).
- Observation feedback loop: model → tool → observation → follow-up model request.
- Permission enforcement: a default policy evaluated before every tool call. Filesystem access is bounded by `WorkspaceBoundary`; the shell tool blocks a few deny-classified command categories by pattern (including printing secret-named variables such as `echo %GROQ_API_KEY%`). `ASK` is an explicit third decision routed to an `ApprovalProvider`: the CLI wires in `CliApprovalProvider`, which prompts y/N at the terminal and rejects on anything else; when no provider is supplied the executor auto-rejects, so ASK behaves as deny.
- Cross-process tool-execution recovery, validated against live Postgres.

**Built for the MVP path (`DIRECTOR_REVIEW_007.md` tasks T1 to T3, closed in `DIRECTOR_REVIEW_009.md`):**

- Composition root (`neptune.application.composition`) and CLI (`python -m neptune`) that build the registries, gateway, tools and `PlanRunner` from a goal and a workspace path.
- The original goal text is passed into every step's context.
- `CliApprovalProvider`: an interactive terminal approval channel implementing `ApprovalProvider`.
- Failure propagation: a tool that reports a failed command (non-zero exit or timeout), a gateway error, a denial or a rejected approval all fail the step, and the CLI reports `not all steps completed` with exit code 1.

**Not verified:**

- Real-model behaviour beyond one run. The acceptance run (see Verified live run) is one goal on one model; reliability across goals, models and platforms is unmeasured. The live tests need `GROQ_API_KEY` and skip without it. Three older live tests (B-008 `test_live_first_agent_turn`, B-009 `test_full_live_agent_loop`, B-011 `test_full_live_agent_loop_dynamic_tools`) still assume the registry was already seeded and fail when run alone on an empty database; they pass in suite order because the CLI tests seed it first. The A-010 and A-011 live tests seed the registry themselves.

**Known limitations (post-MVP):**

- Steps run as independent tasks with no shared turns or observations; richer cross-step conversational context is post-MVP.
- A step is recorded as completed when the model stops requesting tools and no tool call failed; nothing independently verifies that its work was done. A model that makes no tool call and claims success is recorded as completed. Observed live when a test harness gave the model no tool schemas: it answered in prose, claimed a verification it had not performed, and both steps were recorded completed with an empty workspace. The A-011 live test now fails on that.
- Plan- and goal-level resume is post-MVP. Recovery works for an individual task. A crash mid-step leaves the step `RUNNING` with no reconciliation path, and resubmitting a goal creates a new plan.
- Any tool error ends its step and is not fed back to the model: a denial, a rejection, a failed filesystem call (e.g. reading a missing file) or a command that exits non-zero. The model cannot react to the failure and retry within the step.
- Permission enforcement is a tool-boundary policy, not isolation. File tools are confined to the workspace; **shell commands only start in the workspace and are not confined to it** (a command can write elsewhere without a prompt). The shell rules are regex heuristics and can be evaded, and there is no sandbox or container isolation (`SANDBOX_CONTRACT` is unimplemented).
- The legacy YAML `ModelRegistry` is no longer used by production code but has not been deleted; three test modules and `scripts/run_live_groq_smoke_test.py` still import it.
- Not started: MCP-based tool integration, sandboxed execution, multi-agent orchestration, retry/backoff, replanning, and a second real provider.

**Running the tests:** start Postgres first (`docker compose up -d`). With the database down, the suite still reports zero failures but silently skips every database-backed test (41 tests at one full run), including the real-tool integration proofs. With Postgres up and no key, on an empty database: 412 collected, 403 passed, 0 failed, 9 skipped; the 9 skips are live-provider tests that need `GROQ_API_KEY`. With a key, on an empty database: 412 passed, 0 skipped (the live tests executed). `requirements.txt` pins `pytest>=8,<9`; that resolves to pytest 8.4.2 and the suite passed under it (400 passed, 9 skipped, at commit `96237b1`). A locally installed pytest 9.1.1 also passes, so a newer local pytest is environment drift, not a defect, and the pin was not changed.

This list reflects what has been built and tested in this repository, not a roadmap percentage.

## Running Neptune

```text
pip install -r requirements.txt
docker compose up -d                          # Postgres (required); tables and registry data are created on first run
$env:GROQ_API_KEY = "..."                      # PowerShell; use export GROQ_API_KEY=... in sh
$env:PYTHONPATH = "src"                        # there is no installed package; pytest.ini sets this for tests only
python -m neptune "Create hello.txt containing hello, then read it back" --workspace ./some-dir
```

Neptune plans the goal, runs each step, and prints each tool call and the final state of every step. For an `ask`-classified action (installing packages, `git push`, network tools) it shows the command and asks `[y/N]`; anything but `y`/`yes` rejects. Exit codes: 0 every step completed with no tool errors; 1 not all steps completed; 2 usage or environment problem; 3 no valid plan could be produced.

Two things to know before pointing it at a real directory: file tools are confined to `--workspace`, but **shell commands are not**; and "completed" means the model finished without a tool error, not that the result was checked.

**Tested platform:** Windows (shell `cmd.exe`), Python 3.14.5, Postgres via Docker Desktop. Nothing has been run on Linux or macOS and there is no CI. The shell tool uses the platform's default shell (`/bin/sh` on POSIX) and its description now tells the model which shell that is, because a model otherwise assumes a POSIX shell (`sh -c ...`), which does not exist on Windows. POSIX behaviour is untested.

**Verified live run (2026-10-11, commit `96237b1`, real Groq `openai/gpt-oss-120b`):** the goal `Create a file named hello.txt containing hello, then read it and verify its contents.` produced a valid 2-step plan that was persisted and ended `completed`; the real tools ran (`write_file` wrote 5 bytes, `list_directory`, `read_file` returned `hello`); the file on disk was exactly `b'hello'`; and the CLI reported `all steps completed with no tool errors` with exit 0. Verified from the persisted records and the file, not from the CLI summary. A second real-model run asked for a failing command: the model sent `sh -c 'exit 3'`, which genuinely failed on Windows with exit code 1; the step was recorded `failed`, its dependent `skipped`, and the CLI reported `not all steps completed` with exit 1. This is one goal on one model, not a reliability measurement.

**Reproduced live run (2026-10-23, commit `596a910`, real Groq `openai/gpt-oss-120b`):** the same `hello.txt` goal was run again in a fresh workspace and checked from the persisted records and the file. This time the planner produced 4 steps (not 2), all `completed`; the file on disk was exactly `b'hello'`; the CLI exited 0. A failing-command goal (`exit 3`) failed its step at exit code 3, skipped its dependent and exited 1. Full suite with a key: 412 passed, 0 skipped. Record: `docs/ACCEPTANCE_RUN_2026-10-23.md`. This is separate from the 2026-10-11 run above, which remains a summary that was not stored. Still one provider, two goals, Windows only.

## Free / Cheap-First Philosophy

Neptune's economic objective is to build the strongest practical agent infrastructure from free and low-cost resources, while keeping a working baseline that costs nothing to run.

That means preferring open-source components where they're adequate, treating provider free tiers as optional capacity rather than a dependency, and favoring local or self-hosted alternatives (e.g. local Postgres via Docker) where they hold up. Every provider and resource sits behind a contract specifically so it can be replaced without touching core logic.

Temporary credits or promotional access (cloud trial credits, limited-time API keys) are useful burst capital, but they are never treated as an architectural foundation — nothing in the core design assumes they'll still be available tomorrow.

## Repository Guide

- `01_BIBLE/` — the authoritative internal specification: vision, architecture, and frozen principles.
- `02_ARCHITECTURE/` — canonical component relationships, dependency direction, and data flow.
- `03_CONTRACTS/` — the interface contracts each component must satisfy (Model, Provider, Tool, Runtime, etc.).
- `05_DECISIONS/` — ADRs recording every frozen architectural decision.
- `06_REGISTRIES/` — provider/model/resource/tool catalogs and their YAML seed data.
- `14_DEVELOPMENT_ORCHESTRATION/` — the two-agent (Claude A / Claude B) development methodology used to build Neptune itself.
- `src/` — implementation: `core/` (domain, contracts, runtime, registry, resolution, planning), `neptune/` (Model Gateway, providers, tools, permission and approval, observation loop), `infrastructure/` (persistence).
- `scripts/` - repository verification and live-provider probe scripts. The product entry point is `python -m neptune` (`src/neptune/cli.py`).
- `docs/` - `BUILD_METHODOLOGY.md` and dated acceptance-run records (latest: `ACCEPTANCE_RUN_2026-10-23.md`).
- `DIRECTOR_REVIEW_*.md` - read-only audits of the integrated system; the latest, `DIRECTOR_REVIEW_009.md`, is the MVP closure report (it follows the final audit `DIRECTOR_REVIEW_008.md`).
- `tests/` — unit, contract, and integration tests, including live-provider and live-Postgres suites (skip automatically without credentials).
- `DEVELOPMENT_STATE/` — machine-readable task assignments, dependencies, and decisions tracking parallel development.

## Current Next Milestone

The MVP implementation is complete and has been verified end to end with a real model on one goal. Nothing further is scheduled; the post-MVP items under Known limitations are not started.

Four architectural decisions are awaiting director ADR numbering. They are recorded, unnumbered and unapproved, in `DEVELOPMENT_STATE/assignments.yaml`.

## Deep Documentation

This README is intentionally a landing page. For the full specification, design rationale, and internal build methodology, see:

- `01_BIBLE/` — the Neptune Bible (vision, architecture, contracts index)
- `02_ARCHITECTURE/` and `03_CONTRACTS/` — architecture and interface detail
- `05_DECISIONS/00_ADR_INDEX.md` — every architectural decision, in order
- `14_DEVELOPMENT_ORCHESTRATION/` — the internal build methodology (two-agent development, work allocation, director control, git protocol)
- `docs/BUILD_METHODOLOGY.md` — reading order, authority order, and the first-build sequence
- `DEVELOPMENT_STATE/` — live task assignments and dependency tracking
