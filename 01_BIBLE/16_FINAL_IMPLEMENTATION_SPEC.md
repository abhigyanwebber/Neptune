# Neptune Final Implementation Specification

**Status:** NORMATIVE REFERENCE IMPLEMENTATION SPECIFICATION
**Phase:** Final Bible building phase / Phase 1 handoff

## 1. Purpose

This document closes the remaining implementation ambiguity without freezing Neptune to external vendors.

The distinction is deliberate:

- **Architecture is frozen.**
- **Reference implementation choices are proposed starting points for the first build.**
- **External providers remain replaceable through contracts and adapters.**

A builder should be able to begin implementation from this document and the referenced contracts without asking the architecture owner to invent missing system boundaries.

## 2. Reference implementation choices

| Concern | First implementation | Replacement rule |
|---|---|---|
| Primary language | Python | May be replaced if contracts remain intact |
| API/control plane | FastAPI | Adapter/interface boundary required |
| Validation/types | Pydantic | Serialization must preserve schemas |
| Persistence | PostgreSQL | Repository abstraction required |
| ORM/data access | SQLAlchemy + migrations | Replaceable behind repository layer |
| Event storage | PostgreSQL append-only event table | Event contract remains stable |
| Queue/orchestration | Database-backed durable queue for first build | Replaceable by dedicated broker later |
| Model gateway | Neptune Model Gateway | Mandatory internal abstraction |
| Provider normalization | LiteLLM behind the gateway/router boundary | Replaceable |
| Initial inference lane | One currently verified free provider/model candidate | Registry-driven; never hard-coded in agent logic |
| Router | Neptune policy router using capability, quota, health, cost and fallback metadata | Scoring formula is implementation detail |
| Runtime | Docker container runtime | Runtime contract remains stable |
| Initial safe tool | Workspace file read/write + bounded command execution | Tool registry/permission boundary mandatory |
| Permissions | Explicit allow/ask/deny policy engine | Policy implementation replaceable |
| Secrets | Environment/secret-store abstraction; deployment may use GitHub secrets or Doppler | Never stored in task/session context |
| Observability | Structured logs + OpenTelemetry-compatible instrumentation + Sentry candidate | Provider replaceable |
| CI | GitHub Actions | CI provider replaceable |
| Reference persistent host | Oracle Always Free candidate | Deployment target is replaceable |
| Edge/reverse proxy | Cloudflare candidate | Replaceable |
| Local development | Docker Compose | Replaceable |

These choices are implementation defaults, not architectural dependencies.

## 3. Mandatory first vertical slice

Implement only this path first:

```text
Task creation
  -> Session creation
  -> Context assembly
  -> Model Gateway request
  -> Router selection
  -> LiteLLM/provider call
  -> bounded safe tool call
  -> observation/event
  -> checkpoint
  -> verification
  -> task completion/resume
```

The slice is not complete until it survives the Phase 1 tests.

## 4. Mandatory component boundaries

```text
core/
  domain/
  contracts/
  policies/

application/
  task_service/
  session_service/
  execution_service/
  context_service/
  checkpoint_service/

infrastructure/
  persistence/
  events/
  models/
  providers/
  runtime/
  tools/
  observability/
  secrets/

interfaces/
  api/
  cli/

config/
  capability registry
  provider registry
  resource registry
  policy configuration
```

The exact package names may change, but the dependency direction may not.

## 5. Dependency direction

```text
interfaces
    -> application
        -> core

infrastructure
    -> core/application contracts

external providers
    -> infrastructure adapters

project-specific code
    -> Neptune public contracts
```

Core must never import a provider SDK, cloud SDK, model-specific client, or project-specific module.

## 6. State rule

PostgreSQL is the first durable state implementation.

The following must be recoverable without a live model provider:

- task state;
- session metadata;
- turn records;
- event history;
- checkpoints;
- artifact metadata;
- provider/model selection records;
- usage/cost records;
- resource lifecycle records.

Provider-side conversation state may be treated as a cache, never as the sole source of truth.

## 7. Model rule

Agent logic requests capabilities, not provider/model names.

Example:

```yaml
capabilities:
  - coding
  - tool_use
  - structured_output
constraints:
  cost_class_max: free
  context_min: required
```

The router resolves this into a model candidate.

## 8. Tool rule

Every tool call passes through:

```text
agent intent
 -> capability check
 -> permission decision
 -> sandbox
 -> execution
 -> bounded result
 -> event
```

A model cannot grant itself permission.

## 9. Context rule

Context assembly must preserve, in priority order:

1. active task requirements and constraints;
2. current execution state;
3. security/policy instructions;
4. relevant recent interaction state;
5. required tool definitions;
6. selected memory;
7. selected project/repository context;
8. historical material that fits remaining budget.

The first implementation may use deterministic rules. Retrieval/ranking sophistication can evolve later.

## 10. Recovery rule

A runtime kill must not imply task loss.

The recovery path is:

```text
runtime failure
 -> failure event
 -> durable session state
 -> latest valid checkpoint
 -> reconstruct context
 -> retry/resume
```

The first implementation may resume at a coarse checkpoint boundary; exact process-level continuation is not required.

## 11. Economic rule

The first implementation must function with no temporary credits.

Temporary resources may improve:

- throughput;
- latency;
- model quality;
- GPU experiments;
- batch processing;
- production bursts.

They may not be required to prove Neptune's basic correctness.

## 12. Production hardening after vertical slice

Only after the vertical slice passes:

1. second provider;
2. quota accounting;
3. health checks/cooldowns;
4. persistent usage accounting;
5. context compaction;
6. artifact storage;
7. stronger sandbox controls;
8. backup/restore;
9. deployment automation;
10. load/failure testing;
11. local support lane;
12. optional multi-agent execution.

## 13. Explicit non-goals for first build

Do not build:

- a proprietary model;
- a universal cloud manager;
- a full autonomous multi-agent swarm;
- every provider adapter;
- every MCP server;
- a custom vector database;
- a custom auth platform;
- a custom frontend platform;
- project-specific Argus or Workspace OS logic.

## 14. Definition of implementation-ready

Neptune is implementation-ready when the builder can implement the first vertical slice using this specification, the contracts, and the schemas while keeping all provider/cloud choices at the adapter boundary.
