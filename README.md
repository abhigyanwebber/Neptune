# Neptune

**A reusable, project-agnostic agent infrastructure — a provider-agnostic, self-hostable, Claude-Code-like execution environment.**

Specification version: 0.7.1 · Phase: implementation (post-architecture-freeze) · Status: engine subsystems built and tested; no user-facing entry point yet

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

- **Planning** (`core/planning`) turns a goal into an ordered, validated plan: `GoalPlanner` asks the model for structured steps and `PlanExecutor` tracks step status. `PlanRunner` executes a plan by running each step as its own runtime task; steps do not share turns or observations.
- **Resolution** picks concrete capabilities, providers, and resources for a step from the registries (`core/resolution`).
- **Runtime** (`core/runtime`) drives a session turn-by-turn: assemble context, request a model turn, execute any requested tool calls, record the observation, decide whether to continue or complete.
- **Model Gateway** normalizes requests/responses across providers behind `MODEL_CONTRACT`/`PROVIDER_CONTRACT`/`ROUTER_CONTRACT`; the first live adapter is Groq.
- **Tool offering** — `ToolOfferingResolver` turns the canonical tool registry into the tool definitions sent with each model request, and `RuntimeDriver` can supply per-turn context through an optional `context_provider`.
- **Tool Execution** runs tool calls under a boundary that enforces timeouts and output-size limits (`TOOL_CONTRACT`). Before a tool runs, `ToolExecutorService` evaluates a permission policy: a call is allowed, denied, or, for `ask`-classified actions, sent to an `ApprovalProvider`. A denied or unapproved call never reaches the tool.
- **Observation** feeds tool results back to the model as deterministic, replayable messages (ADR-043).
- **Checkpoint / Recovery** persists state to Postgres so a run can resume in a fresh process after a stop or crash.

## Current State

Neptune's engine subsystems are built and tested. What is missing is the thing that runs them: nothing outside the test suite builds the dependency graph, so **there is no user-facing entry point yet** — a user cannot submit a goal today (`DIRECTOR_REVIEW_007.md`).

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
- Permission enforcement: a default policy evaluated before every tool call. Filesystem access is bounded by `WorkspaceBoundary`; the shell tool blocks a few deny-classified command categories by pattern. `ASK` is an explicit third decision routed to a replaceable `ApprovalProvider`; the only production provider auto-rejects, so ASK currently behaves as deny.
- Cross-process tool-execution recovery, validated against live Postgres.

**Not built yet (remaining MVP work, per `DIRECTOR_REVIEW_007.md`):**

- A composition root and CLI entry point that builds the registries, gateway, tools and `PlanRunner` from a goal and a workspace path.
- Passing the goal text into each step's context (steps currently see only their own title and description).
- An interactive approval channel implementing `ApprovalProvider`.
- Live end-to-end validation with a real provider credential.

**Not verified:**

- The live Groq tests for `GoalPlanner` (A-010) and `PlanRunner` (A-011) have never run, because no `GROQ_API_KEY` was available where they were verified. Plan quality from a real model, and the goal → plan → execute path against a real provider, are unverified.

**Known limitations (post-MVP):**

- Steps run as independent tasks with no shared turns or observations; richer cross-step conversational context is post-MVP.
- Plan- and goal-level resume is post-MVP. Recovery works for an individual task. A crash mid-step leaves the step `RUNNING` with no reconciliation path, and resubmitting a goal creates a new plan.
- A denial or rejection ends its step; it is not yet fed back to the model as an observation.
- Permission enforcement is a tool-boundary policy, not isolation. The shell rules are regex heuristics and can be evaded, and there is no sandbox or container isolation (`SANDBOX_CONTRACT` is unimplemented).
- The legacy YAML `ModelRegistry` is no longer used by production code but has not been deleted; three test modules and `scripts/run_live_groq_smoke_test.py` still import it.
- Not started: MCP-based tool integration, sandboxed execution, multi-agent orchestration, retry/backoff, replanning, and a second real provider.

**Running the tests:** start Postgres first (`docker compose up -d`). With the database down, the suite still reports zero failures but silently skips every database-backed test, including the real-tool integration proofs (about 33 tests at the last review). Live-provider tests skip without a credential.

This list reflects what has been built and tested in this repository, not a roadmap percentage.

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
- `scripts/` — repository verification and live-provider probe scripts (not a product entry point).
- `DIRECTOR_REVIEW_*.md` — read-only audits of the integrated system; the latest, `DIRECTOR_REVIEW_007.md`, is the current product-readiness assessment.
- `tests/` — unit, contract, and integration tests, including live-provider and live-Postgres suites (skip automatically without credentials).
- `DEVELOPMENT_STATE/` — machine-readable task assignments, dependencies, and decisions tracking parallel development.

## Current Next Milestone

The remaining MVP implementation is the product entry point (`DIRECTOR_REVIEW_007.md`, tasks T1 to T4): a composition root and CLI that take a goal and a workspace path, build the registries, gateway, tools and `PlanRunner`, pass the goal text into each step, prompt interactively for approval behind `ApprovalProvider`, and are then validated once end to end with a real provider credential. None of this exists in the repository yet.

Four architectural decisions are awaiting director ADR numbering. They are recorded, unnumbered and unapproved, in `DEVELOPMENT_STATE/assignments.yaml`.

## Deep Documentation

This README is intentionally a landing page. For the full specification, design rationale, and internal build methodology, see:

- `01_BIBLE/` — the Neptune Bible (vision, architecture, contracts index)
- `02_ARCHITECTURE/` and `03_CONTRACTS/` — architecture and interface detail
- `05_DECISIONS/00_ADR_INDEX.md` — every architectural decision, in order
- `14_DEVELOPMENT_ORCHESTRATION/` — the internal build methodology (two-agent development, work allocation, director control, git protocol)
- `docs/BUILD_METHODOLOGY.md` — reading order, authority order, and the first-build sequence
- `DEVELOPMENT_STATE/` — live task assignments and dependency tracking
