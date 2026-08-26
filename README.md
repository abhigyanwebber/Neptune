# Neptune

**A reusable, project-agnostic agent infrastructure — a provider-agnostic, self-hostable, Claude-Code-like execution environment.**

Version: 0.7.1 · Phase: implementation (post-architecture-freeze) · Status: core layers built and validated; end-to-end wiring in progress

## What is Neptune?

Neptune is infrastructure for running AI agents in production, without betting the whole system on any single model provider, framework, or paid tier.

Most agent projects hard-wire themselves to one LLM API and one execution harness. When that provider changes pricing, rate-limits, or deprecates a model, the project breaks. Neptune's answer is to treat models, tools, and resources as swappable components behind stable contracts, so the agent runtime keeps working even as the providers underneath it change.

Concretely, Neptune is a set of layered, contract-driven components — task/session/turn state, a model gateway, a tool execution boundary, a registry of providers and capabilities, and a recovery-capable runtime — designed to be reused across future projects rather than rebuilt per-project.

## Why Neptune?

- **Claude-Code-like production workflow** — a durable agent loop (goal → plan → model → tool → observation → next turn) rather than a one-shot script.
- **Provider/model freedom** — providers are adapters behind a gateway contract; no provider name is hard-coded into core logic.
- **Cost control** — built free/cheap-first, with paid or rate-limited resources treated as optional burst capacity, not a foundation.
- **Reusable infrastructure** — the runtime, registries, and contracts are meant to outlive any single project built on top of them.
- **Durable execution and recovery** — state (tasks, turns, checkpoints, events) is persisted so a run can stop and resume across process restarts.

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

- **Planning** turns a goal into an ordered set of steps (`core/planning`), independent of any particular runtime turn.
- **Resolution** picks concrete capabilities, providers, and resources for a step from the registries (`core/resolution`).
- **Runtime** (`core/runtime`) drives a session turn-by-turn: assemble context, request a model turn, execute any requested tool calls, record the observation, decide whether to continue or complete.
- **Model Gateway** normalizes requests/responses across providers behind `MODEL_CONTRACT`/`PROVIDER_CONTRACT`/`ROUTER_CONTRACT`; the first live adapter is Groq.
- **Tool Execution** runs tool calls under a boundary that enforces timeouts and output-size limits (`TOOL_CONTRACT`).
- **Observation** feeds tool results back to the model as deterministic, replayable messages (ADR-043).
- **Checkpoint / Recovery** persists state to Postgres so a run can resume in a fresh process after a stop or crash.

## Current State

**Implemented and validated:**

- Core domain + persistence: Task/Agent/Session/Turn/Event/Checkpoint over Postgres, with a process-boundary recovery test.
- Registries: capability, provider, resource, and tool catalogs, with a YAML loader, JSON snapshot exporter, and audit trail.
- Resolution layer: capability → provider/resource selection and dependency expansion, independent of execution.
- Planning layer: `Goal`/`Plan`/`PlanStep` contracts and a `PlanExecutor` that runs hand-authored plans (no AI-driven plan generation yet).
- Model Gateway: `MODEL_CONTRACT`/`PROVIDER_CONTRACT`/`ROUTER_CONTRACT` implemented, with a live Groq adapter validated against the real API.
- Tool execution boundary: `ToolExecutor`, `EchoTool`, and a registry adapter, with timeout and output-size enforcement.
- Observation feedback loop: model → tool → observation → follow-up model request, driven by `run_observation_loop`.
- Cross-process tool-execution recovery, validated against live Postgres via a `ToolPortAdapter` bridging the Runtime's `ToolPort` contract to the real `ToolExecutor` (ADR-042).

**Currently under integration:**

- Wiring the real Model Gateway into `AgentRuntime` in place of the test-only `FakeModelGateway`.
- Cutting over remaining legacy registry consumers to the canonical registry (audited in `DIRECTOR_LEGACY_REGISTRY_AUDIT.md`; cutover itself not yet performed).

**Not yet started:**

- AI-driven plan generation (planning currently executes hand-authored plans only).
- MCP-based tool integration, sandboxed execution, and multi-agent orchestration.

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
- `src/` — implementation: `core/` (domain, contracts, runtime, registry, resolution, planning), `neptune/` (Model Gateway, providers, tools, observation loop), `infrastructure/` (persistence).
- `tests/` — unit, contract, and integration tests, including live-provider and live-Postgres suites (skip automatically without credentials).
- `DEVELOPMENT_STATE/` — machine-readable task assignments, dependencies, and decisions tracking parallel development.

## Current Next Milestone

Wire the validated Model Gateway into the Runtime so a live provider drives real agent turns end-to-end, and complete the legacy registry cutover so all production code paths read from the canonical registry. Both are scoped and tracked in `DEVELOPMENT_STATE/dependencies.yaml` and `DIRECTOR_LEGACY_REGISTRY_AUDIT.md`.

## Deep Documentation

This README is intentionally a landing page. For the full specification, design rationale, and internal build methodology, see:

- `01_BIBLE/` — the Neptune Bible (vision, architecture, contracts index)
- `02_ARCHITECTURE/` and `03_CONTRACTS/` — architecture and interface detail
- `05_DECISIONS/00_ADR_INDEX.md` — every architectural decision, in order
- `14_DEVELOPMENT_ORCHESTRATION/` — the internal build methodology (two-agent development, work allocation, director control, git protocol)
- `docs/BUILD_METHODOLOGY.md` — reading order, authority order, and the first-build sequence
- `DEVELOPMENT_STATE/` — live task assignments and dependency tracking
