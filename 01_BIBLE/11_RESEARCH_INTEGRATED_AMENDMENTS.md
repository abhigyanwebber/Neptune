# 34. Research-Derived Architecture Amendments — v0.2

This section records the architectural conclusions added after re-reading the three source reports together.

These amendments **supersede weaker or more tentative statements in v0.1 where they conflict**. They do not change the project-agnostic nature of the infrastructure.

## 34.1 Source hierarchy

The infrastructure research establishes three distinct but connected domains:

```text
LLM / MODEL SUPPLY
        ↓
AGENTIC HARNESS
        ↓
GENERAL INFRASTRUCTURE
```

The model report establishes the economic and reliability problem of the model supply layer.

The harness report establishes the execution architecture required to turn models into useful agents.

The student/free-infrastructure report establishes the resource-acquisition and lifecycle strategy for operating the whole system cheaply.

The Bible must preserve these as separate architectural concerns.

## 34.2 Historical Claude Code source is not the architecture specification

The leaked Claude Code repository is treated only as historical evidence.

The research explicitly warns that the shipping product has diverged from the leaked repository and has subsequently added hooks, skills, subagents, MCP tool search, dynamic workflows, and sandboxed execution.

Therefore:

**We copy architectural ideas, not leaked implementation assumptions.**

The infrastructure should be based on documented behavior, open-source implementations, cross-tool convergence, and our own experiments.

## 34.3 Harness-first conclusion

The reports converge on an important conclusion:

> At realistic budget levels, orchestration quality, context management, routing discipline, tool reliability, and recovery produce larger practical differences than constantly hunting for the single "best" model.

This does **not** mean the model is unimportant. Model quality becomes decisive when the selected model is too weak to sustain a long tool loop.

Therefore the infrastructure must optimize both:

```text
MODEL QUALITY
        +
HARNESS QUALITY
```

rather than treating either as sufficient alone.

---

# 35. Agent Loop Architecture

The research identifies three useful loop families.

## 35.1 Plan → Execute → Verify

Characteristics:

- explicit planning before execution;
- checkpoints;
- useful for bounded tasks;
- easier to reason about operationally.

## 35.2 Iterative Agent Loop

```text
observe
  ↓
reason
  ↓
act
  ↓
observe
  ↓
repeat
```

Characteristics:

- tight coding loop;
- incremental correction;
- strong fit for interactive software engineering.

## 35.3 Event-Stream / Platform Loop

Every significant interaction becomes an event:

```text
task
 ↓
model request
 ↓
tool request
 ↓
tool result
 ↓
model request
 ↓
verification
```

Characteristics:

- observable;
- replayable;
- programmable;
- naturally suited to multi-agent systems.

## 35.4 Infrastructure Decision

The infrastructure should support a **hybrid loop**:

```text
TASK
 ↓
PLAN
 ↓
ITERATIVE EXECUTION LOOP
 ↓
VERIFICATION
 ↓
CHECKPOINT / EVENT RECORD
 ↓
RECOVERY OR COMPLETION
```

The loop itself should emit events.

This gives us the bounded-task advantages of explicit planning and the flexibility of iterative execution, while preserving event-level observability.

---

# 36. Tool Architecture

## 36.1 Tool Taxonomy

Tools should be categorized by capability rather than provider.

### Core local tools

- read
- write
- edit
- search
- grep
- glob
- shell
- Git
- test
- build

### Environment tools

- browser
- web fetch
- web search
- package manager
- process management

### External tools

- APIs
- databases
- cloud services
- Git hosting
- SaaS services

### Extension tools

- MCP servers

## 36.2 Tool Definition Loading

Tool definitions themselves consume context.

Therefore the infrastructure should support **deferred tool-definition loading**:

```text
Agent starts
    ↓
Tool names / capability summaries
    ↓
Agent requests tool
    ↓
Full definition loaded
    ↓
Tool executed
```

This is preferred over injecting every tool schema into every model call.

## 36.3 Tool Output Controls

Every execution tool should support:

- timeout;
- output-size limit;
- truncation;
- structured result;
- error classification;
- cancellation;
- retry policy where safe.

Large tool output must never be allowed to consume the entire context window unchecked.

---

# 37. Context Architecture — Expanded

## 37.1 Context Is a Managed Resource

Context is not merely conversation history.

It is a budget containing:

```text
instructions
task
repository knowledge
file contents
tool definitions
tool outputs
memory
model outputs
verification state
```

The Context Manager therefore owns the question:

> What information deserves to occupy the next model call?

## 37.2 Repository Understanding

The infrastructure should support multiple repository-understanding strategies:

- symbol/index based maps;
- AST/tree-sitter based maps;
- grep/search retrieval;
- LSP information;
- Git history;
- explicit instruction files.

No single repository map implementation is mandatory.

## 37.3 Compaction

Compaction should be triggered by:

- context budget threshold;
- excessive tool output;
- repeated low-value history;
- explicit operator request;
- model-specific context constraints.

Compaction should preferentially remove or summarize:

1. stale tool output;
2. redundant conversational material;
3. already-resolved intermediate reasoning.

It must preserve:

1. current user task;
2. active constraints;
3. critical decisions;
4. relevant code/state;
5. unresolved problems;
6. important verification results.

## 37.4 Thrashing Guard

The infrastructure should detect repeated oversized or self-amplifying tool interactions.

Example:

```text
tool output
 ↓
context grows
 ↓
model requests larger output
 ↓
context grows again
 ↓
repeat
```

Instead of allowing infinite growth, the system should:

```text
detect
 ↓
truncate / summarize
 ↓
retry if safe
 ↓
abort with diagnostic if thrashing continues
```

---

# 38. Memory Architecture — Expanded

The reports demonstrate that different harnesses use different memory mechanisms.

The infrastructure should combine their strongest concepts without copying one implementation.

## 38.1 Memory tiers

```text
T0 — CURRENT CONTEXT
T1 — SESSION MEMORY
T2 — TASK MEMORY
T3 — PROJECT MEMORY
T4 — INFRASTRUCTURE MEMORY
T5 — ARCHIVAL HISTORY
```

## 38.2 Persistent instruction hierarchy

A future implementation should support layered instructions:

```text
global
  ↓
workspace
  ↓
project
  ↓
directory
  ↓
task
```

More specific instructions may refine broader instructions but must not silently violate security policies.

## 38.3 Memory isolation

Project memory must be namespaced.

```text
Infrastructure memory
        │
        ├── Project A memory
        ├── Project B memory
        └── Project C memory
```

No project should automatically inherit another project's private memory.

---

# 39. Sessions and Checkpoints

## 39.1 Session Requirements

A session must be:

- resumable;
- inspectable;
- attributable to a task;
- associated with an agent;
- associated with model usage;
- associated with tool execution;
- recoverable after runtime failure.

## 39.2 Checkpoint Requirements

A checkpoint should capture enough state to restore meaningful execution.

Potential checkpoint components:

```text
agent state
task state
context summary
Git state
workspace identity
tool state where applicable
model/provider metadata
runtime metadata
```

## 39.3 Git vs Checkpoint

Git is not a complete replacement for agent checkpoints.

Git stores code history.

Agent checkpoints store execution state.

Therefore:

```text
Git = artifact/version memory
Checkpoint = execution memory
Event stream = operational history
```

These three systems are complementary.

---

# 40. Multi-Agent Architecture — Expanded

## 40.1 Multi-Agent Is a Capability, Not a Default

The infrastructure must support multi-agent execution without forcing every task into a multi-agent workflow.

Single-agent execution remains the simplest mode.

## 40.2 Agent Isolation

Each subagent should have:

- its own context;
- bounded tools;
- bounded permissions;
- explicit task identity;
- explicit parent relationship;
- optional isolated worktree/runtime.

## 40.3 Parent / Child Model

```text
Coordinator
   │
   ├── Worker A
   ├── Worker B
   └── Reviewer
```

The parent should receive structured summaries rather than every child tool call.

This prevents child activity from flooding the parent's context.

## 40.4 Parallel Work

Parallel agents should normally operate on:

- separate worktrees;
- separate sandboxes;
- separate task identities.

Shared mutable state requires explicit coordination.

## 40.5 Candidate Substrates

Research identifies OpenHands as the strongest open multi-agent substrate in the surveyed landscape, with Goose also offering useful subagent/recipe/MCP patterns.

These remain **candidate external runtimes**, not architectural dependencies.

---

# 41. Runtime Architecture — Expanded

## 41.1 Runtime Categories

The infrastructure should distinguish:

### Interactive Runtime

For human-supervised coding.

### Autonomous Runtime

For bounded tasks with limited supervision.

### Batch Runtime

For repeatable non-interactive work.

### Multi-Agent Runtime

For coordinated workers.

### Ephemeral Runtime

Created for a task and destroyed afterward.

### Persistent Runtime

Maintains a long-lived service or agent process.

## 41.2 Runtime Adapter

Each runtime adapter must translate its native semantics into the infrastructure's standard runtime contract.

```text
Core Runtime Interface
        ↑
        │
 ┌──────┼─────────┐
 │      │         │
OpenHands Docker  CLI
```

---

# 42. Permission Architecture — Expanded

The reports identify four broad permission architectures:

1. harness-enforced ask/allow/deny;
2. separated sandbox capability + approval policy;
3. mode-based tool groups;
4. approval-first toggle systems.

The infrastructure adopts the strongest conceptual combination:

```text
CAPABILITY
     +
SANDBOX
     +
POLICY
     +
APPROVAL
```

## 42.1 Capability

What the runtime is technically capable of doing.

## 42.2 Policy

What the agent is permitted to request.

## 42.3 Approval

Whether a human or higher-level policy must authorize a particular operation.

## 42.4 Sandbox

Where the operation is allowed to execute.

These are distinct.

---

# 43. Policy Precedence

Proposed precedence:

```text
GLOBAL DENY
     >
WORKSPACE DENY
     >
TASK DENY
     >
EXPLICIT APPROVAL
     >
ALLOW RULE
```

A deny rule should be able to prevent a capability from even being presented to the model when practical.

## 43.1 Policy Examples

```text
read repository       → allow
edit workspace        → allow
run tests             → allow
install package       → ask
network access        → ask
push Git branch       → ask
delete remote branch  → deny/strong approval
production migration  → deny/strong approval
secret export         → deny
```

These are examples, not frozen defaults.

---

# 44. Hooks / Lifecycle Automation

Hooks should be treated as an infrastructure extension mechanism.

Potential lifecycle events:

```text
SystemStart
SessionStart
TaskStart
PromptReceived
BeforeContextBuild
BeforeModelCall
AfterModelCall
BeforeToolCall
PermissionRequest
AfterToolCall
VerificationStart
VerificationEnd
Checkpoint
TaskComplete
TaskFailure
SessionEnd
```

Hooks may be used for:

- validation;
- policy checks;
- telemetry;
- secret injection;
- context modification;
- tool veto;
- artifact processing;
- cleanup.

Hooks must themselves be subject to permission and security rules.

---

# 45. Skills Architecture — Expanded

Skills should be portable behavior packages.

A skill should contain:

```text
identity
purpose
instructions
required capabilities
optional capabilities
input schema
output schema
verification procedure
security constraints
```

Skill loading should be dynamic.

A skill should not permanently consume model context merely because it exists.

---

# 46. Model Supply Architecture — Expanded

## 46.1 Provider Volatility

The model research documents repeated provider/model changes:

- free catalogs disappearing;
- model delistings;
- free tiers ending;
- quotas changing;
- providers changing catalog composition without long migration windows.

Therefore:

**Model availability is runtime data, not static architecture.**

## 46.2 Capability Pinning

Do not pin the infrastructure to:

```text
provider = X
model = Y
```

as the only definition.

Instead pin to:

```text
capability = coding
quality >= threshold
context >= threshold
tool_use = required
cost <= budget
```

Then resolve to current providers.

## 46.3 Dual-Homing

Where feasible, important model lanes should have multiple provider implementations.

Example:

```text
coding capability
    │
    ├── Provider A / Model X
    └── Provider B / Model X
```

Dual-homing the same model family is especially valuable because provider failure does not necessarily change model behavior.

## 46.4 Provider Reliability Record

Provider health should track:

- uptime;
- latency;
- rate-limit frequency;
- catalog stability;
- error rate;
- historical failures;
- quota remaining.

The provider with the best model is not automatically the provider with the best operational value.

---

# 47. Model Routing — Expanded

## 47.1 Routing Inputs

The router may use:

```text
task class
model capability
context requirement
tool-calling requirement
provider health
remaining quota
estimated cost
latency
failure history
current session model
cache state
escalation state
```

## 47.2 Routing Outputs

The router should return:

```text
selected provider
selected model
reason
expected capability
fallback chain
quota impact
cost class
```

## 47.3 Routing Lanes

Initial conceptual lanes:

```text
LOCAL SUPPORT
FREE PRIMARY
FREE SECONDARY
CHEAP OVERFLOW
STRONG ESCALATION
FRONTIER BURST
```

The exact models are maintained outside the core architecture in a provider registry.

---

# 48. Model Specialization

Research supports role specialization for cost efficiency.

Potential roles:

| Role | Desired property |
|---|---|
| Router | fast + structured |
| Classifier | cheap + reliable |
| Context compressor | cheap + stable |
| Extraction worker | cheap + high throughput |
| Coder | strong coding ability |
| Planner | strong reasoning |
| Reviewer | independent verification |
| Debugger | strong diagnosis |
| Escalation model | maximum available quality |

A model should be selected for the role it performs, not merely because it is the strongest available model.

---

# 49. Model Switching and State Ownership

A crucial rule from the LLM research:

> No external model provider should hold state that the agent infrastructure cannot reconstruct.

The infrastructure therefore owns:

- conversation state;
- task state;
- memory;
- checkpoints;
- summaries;
- tool history;
- provider metadata.

Provider-side state may be used for optimization, but must not be a single point of recovery.

## 49.1 Safe Switching Points

Prefer:

```text
turn boundary
checkpoint
compaction boundary
task boundary
explicit escalation
```

Avoid switching providers in the middle of an active generation.

---

# 50. Cache Architecture

Prompt caching creates a real tradeoff.

A single model/provider can benefit from stable prefixes.

Multi-provider routing can destroy cache warmth.

Therefore the router must consider:

```text
expected quality
+
cost
+
quota
+
health
+
cache value
```

A slightly cheaper provider is not necessarily better if switching causes a large cache penalty.

---

# 51. Local Model Strategy

The research concludes that the current laptop is not suitable as the primary large-model coding server.

The local tier is therefore optimized for:

- routing;
- classification;
- summarization;
- context compression;
- offline fallback;
- lightweight embeddings where practical;
- infrastructure administration.

Local models should not be selected because they are impressive on a benchmark alone.

They must be evaluated on:

- latency;
- RAM usage;
- structured output;
- reliability;
- useful accuracy;
- integration cost.

---

# 52. Infrastructure Resource Strategy — Expanded

## 52.1 Resource Pool

The infrastructure should maintain a registry across:

```text
models
compute
storage
databases
deployment
CI/CD
secrets
monitoring
domains
DNS/CDN
GPU
automation
```

## 52.2 Claim vs Activation

Student resources have different clocks.

Separate:

```text
CLAIM NOW
```

from:

```text
ACTIVATE NOW
```

A benefit can be secured without immediately consuming a time-limited trial.

This distinction must be represented in the resource registry.

## 52.3 Resource States

```text
DISCOVERED
ELIGIBLE
CLAIMED
ACTIVE
DORMANT
EXPIRING
EXPIRED
REPLACED
```

## 52.4 Expiration Tracking

Every temporary resource must have:

- activation date;
- expiration date;
- remaining balance;
- intended use;
- replacement;
- migration plan.

---

# 53. Azure Strategy — Expanded

Azure is explicitly classified as **burst capital**, not the permanent backbone.

Student credits cannot be assumed to cover:

- Azure OpenAI;
- Marketplace third-party software;
- paid DevOps services;
- ExpressRoute;
- support plans.

GPU quota is a separate risk and may require approval.

Therefore the infrastructure should check quota and eligibility **before** designing workloads around Azure GPU.

## 53.1 Appropriate Azure Uses

Potential high-value uses:

- short GPU experiments if quota is approved;
- temporary high-compute jobs;
- staging;
- controlled deployment sprints;
- temporary persistent services;
- database experiments;
- CI/CD workloads;
- burst inference where the specific service is eligible.

## 53.2 Azure Exit Rule

Any service created with expiring credits must have a documented exit path:

```text
Azure resource
    ↓
export / backup
    ↓
alternative provider
    ↓
migration test
    ↓
shutdown
```

---

# 54. Free Backbone Strategy

The student report identifies a broad $0/month baseline containing candidates for:

```text
Git + CI/CD
Domains + DNS
Frontend
API
Database
Authentication
Secrets
Monitoring
LLM inference
GPU notebooks
Persistent CPU
Scraping
```

Candidate services include:

- GitHub Pro / Actions;
- Cloudflare DNS/CDN/Workers;
- Vercel / Netlify;
- Render;
- Supabase / Neon / MongoDB Atlas;
- Clerk;
- Doppler / 1Password;
- Sentry / New Relic;
- Groq / Cerebras / Gemini / Mistral / Hugging Face / OpenRouter;
- Kaggle / Colab;
- Oracle Cloud Always Free;
- Zyte Scrapy Cloud.

These are **resource candidates**, not architectural dependencies.

---

# 55. Free-Tier Failure Assumptions

The free baseline has real constraints:

- sleeping services;
- suspended databases;
- cold starts;
- egress caps;
- GPU scarcity;
- rate limits;
- no always-on large-model GPU;
- limited storage;
- provider terms changing.

Therefore the infrastructure must distinguish:

```text
FREE
```

from:

```text
PRODUCTION-SUITABLE FOR THIS WORKLOAD
```

A free resource is only promoted to a production role after its failure characteristics are understood.

---

# 56. Student Program Strategy

Student status is a resource-acquisition mechanism, not an architecture.

The infrastructure may exploit legitimate student benefits while the eligibility remains valid.

The resource registry must record:

- eligibility;
- verification method;
- renewal cycle;
- card requirement;
- geographic restrictions;
- activation clock;
- benefit value;
- terms;
- replacement.

## 56.1 Startup / Incubator Path

The research also identifies a separate path:

```text
Student
   ↓
legitimate project / venture
   ↓
university incubator / E-Cell / AIC / startup ecosystem
   ↓
startup cloud programs
```

This must not be conflated with student benefits.

Startup credits are available only when the relevant eligibility conditions are genuinely met.

---

# 57. Cost Architecture

The infrastructure should operate in three economic modes.

## Mode A — $0 Backbone

Use:

- free model tiers;
- local support models;
- free compute;
- free databases;
- free deployment;
- free monitoring;
- student benefits.

## Mode B — Minimal Paid Overflow

Use small paid model spend only when free capacity is exhausted.

## Mode C — Burst Capital

Use:

- Azure credits;
- temporary GPU credits;
- trials;
- startup credits;
- frontier credits

for high-value work that cannot be done efficiently by Mode A/B.

The system should be capable of returning from Mode C to Mode A/B.

---

# 58. Resource Economics

The infrastructure should calculate the value of a resource based on:

```text
capability
×
reliability
×
quota
×
duration
÷
cost
```

This is a conceptual metric, not a final formula.

For temporary credits, also consider:

```text
expiration urgency
+
replacement difficulty
+
migration cost
```

The best resource is not always the one with the largest nominal credit value.

---

# 59. Observability Architecture — Expanded

Observability should be event-driven.

Every important action should be attributable to:

```text
resource
provider
model
agent
task
session
runtime
tool
user
```

## 59.1 Metrics

### Model

- request count;
- tokens;
- latency;
- errors;
- cost;
- quota.

### Agent

- task completion;
- retries;
- tool calls;
- turns;
- escalations;
- failures.

### Runtime

- CPU;
- memory;
- execution duration;
- sandbox failures;
- process failures.

### Provider

- availability;
- latency;
- quota;
- catalog changes;
- failure rate.

---

# 60. Artifact and Audit Model

The infrastructure should preserve important artifacts:

```text
task specification
plan
context summary
tool results
code diff
tests
logs
checkpoint
final result
```

Sensitive data should be redacted according to policy.

Artifacts must be linked to task/session IDs.

---

# 61. Backup and Disaster Recovery

The infrastructure must define recovery classes.

### R0 — Disposable

Caches and temporary runtime state.

### R1 — Recoverable

Sessions and temporary artifacts.

### R2 — Important

Agent state, task records, memory, event logs.

### R3 — Critical

Infrastructure configuration, provider registry, secrets metadata, architectural specifications.

The actual secret values should not be stored in ordinary backups unless encrypted and explicitly intended.

---

# 62. Dependency Rules

The following rules are added to the architecture:

### D1

Core interfaces must not import provider-specific SDKs.

### D2

Provider adapters may depend on core interfaces.

### D3

Projects may depend on core infrastructure APIs.

### D4

Projects should not depend directly on temporary infrastructure providers unless explicitly justified.

### D5

A runtime may depend on tools, but tools should not depend on a specific runtime.

### D6

State storage must be accessed through a state abstraction.

### D7

Model providers must be accessed through the model gateway.

### D8

Secrets must be accessed through a secret abstraction.

### D9

External side effects must pass through permission-aware execution.

### D10

Security policy must be able to deny an operation regardless of model instruction.

---

# 63. Core vs Adapter Boundary

## Core

Owns:

- interfaces;
- task model;
- agent model;
- context model;
- state model;
- event model;
- permission semantics;
- routing semantics;
- observability schema.

## Adapters

Own:

- LiteLLM integration;
- OpenHands integration;
- Docker integration;
- GitHub integration;
- provider SDKs;
- database drivers;
- monitoring SDKs;
- cloud APIs.

This is the main anti-lock-in boundary.

---

# 64. Component Contract Template

Every future component specification must contain:

```text
1. Purpose
2. Responsibilities
3. Non-responsibilities
4. Inputs
5. Outputs
6. State owned
7. State consumed
8. Dependencies
9. Permissions required
10. Failure modes
11. Recovery behavior
12. Events emitted
13. Metrics emitted
14. Security constraints
15. Extension points
16. Replacement strategy
17. Test strategy
18. Resource requirements
```

A component without this contract is not implementation-ready.

---

# 65. Initial Component Ownership Matrix

| Component | Owns | Must not own |
|---|---|---|
| Model Gateway | normalized inference | task planning |
| Model Registry | model metadata | runtime state |
| Router | model/provider selection | agent memory |
| Agent Runtime | execution lifecycle | provider credentials policy |
| Orchestrator | task/agent coordination | raw provider logic |
| Context Manager | context construction | durable project data |
| Memory Manager | memory lifecycle | transient tool output |
| State Store | persistence | business decisions |
| Event Store | event history | current policy |
| Tool Registry | tool metadata | tool authorization |
| Permission Engine | authorization | actual execution |
| Sandbox Manager | isolation | task planning |
| MCP Manager | MCP lifecycle/registration | unrestricted permissions |
| Secret Manager | credential access | arbitrary tool execution |
| Usage Tracker | cost/quota telemetry | routing decisions directly |
| Health Manager | resource health | task semantics |
| Artifact Manager | execution artifacts | provider selection |

---

# 66. Open Questions Reclassified

The previous open questions are now divided into implementation blockers and experiments.

## Architecture blockers

1. Exact AgentRuntime contract.
2. Exact Task model.
3. Exact Event schema.
4. State/event relationship.
5. Core vs adapter package boundary.
6. Permission policy representation.

## Experimental

7. Best context ranking method.
8. Compaction trigger thresholds.
9. Best sandbox implementation.
10. Model capability scoring.
11. Provider health scoring.
12. Routing algorithm.
13. Escalation threshold.
14. Multi-agent coordination protocol.
15. Best repository map implementation.

## Operational

16. Backup frequency.
17. Resource lifecycle automation.
18. Provider quota polling.
19. Cost alert thresholds.
20. Failure notification strategy.

---

# 67. Phase 0 Completion Criteria — Revised

Phase 0 is complete only when:

### Architecture

- six layers are documented;
- ownership boundaries are documented;
- dependency direction is frozen;
- core/adapters boundary is frozen.

### Models

- model gateway contract exists;
- model registry schema exists;
- routing inputs/outputs are defined;
- provider lifecycle model exists.

### Agents

- agent lifecycle is defined;
- runtime contract exists;
- task model exists;
- recovery model exists.

### Execution

- tool taxonomy exists;
- permission model exists;
- sandbox model exists;
- MCP integration boundary exists.

### Context

- context sources are defined;
- ranking model is specified;
- compaction semantics are specified;
- memory tiers are defined.

### State

- state ownership is defined;
- event model exists;
- checkpoint semantics exist;
- artifact model exists.

### Operations

- secrets boundary exists;
- observability schema exists;
- resource lifecycle schema exists;
- backup classes exist.

### Resources

- durable resources are separated from expiring resources;
- claim-vs-activation policy exists;
- Azure burst policy exists;
- provider replacement strategy exists.

---

# 68. Research-to-Architecture Traceability

The following traceability must remain in the Bible.

| Research observation | Architectural response |
|---|---|
| Free provider catalogs change rapidly | Multi-provider registry + routing |
| Provider quotas fail | Quota-aware fallback |
| Same model can be dual-homed | Capability/provider separation |
| Model switching loses cache warmth | Cache-aware routing + boundary switching |
| Model state cannot be migrated | Infrastructure owns state |
| Harness architecture strongly affects workflow | Harness/runtime abstraction |
| Agent loop needs verification | Verify stage + events |
| Tool output can explode context | output limits + thrashing guard |
| Context needs active management | Context Manager |
| Git provides artifact memory | Git/worktree integration |
| Sessions need resume/fork | Session + checkpoint model |
| Subagents need isolated context | child-agent isolation |
| Event streams improve replay | Event Store |
| Sandbox + policy is safer | separated permission/sandbox layers |
| Hooks provide lifecycle control | Hook system |
| Skills provide reusable behavior | Skill system |
| Student credits expire | Resource lifecycle |
| Azure GPU quota is uncertain | quota validation before GPU planning |
| Free services sleep/cap bandwidth | workload suitability classification |
| Student programs change | verification date + resource registry |
| Startup credits are a different eligibility path | separate startup-resource class |

---

# 69. Revised ADRs

## ADR-016 — Use a hybrid agent loop

**Status:** DECISION

The core loop combines explicit planning, iterative execution, verification, checkpointing, and event recording.

## ADR-017 — Treat context as a managed resource

**Status:** FOUNDATION

Context is actively constructed, ranked, compressed, persisted, and restored.

## ADR-018 — Tool definitions should support deferred loading

**Status:** PROPOSED

Full tool schemas should be loaded when needed rather than always consuming model context.

## ADR-019 — Agent state is infrastructure-owned

**Status:** FOUNDATION

No provider or runtime may own unrecoverable agent state.

## ADR-020 — Permission and sandbox are separate concepts

**Status:** FOUNDATION

Capability, authorization, approval, and isolation are distinct layers.

## ADR-021 — Event records are first-class infrastructure state

**Status:** PROPOSED

Important execution actions generate durable events.

## ADR-022 — Multi-agent execution is optional

**Status:** FOUNDATION

The system supports multi-agent execution without requiring it.

## ADR-023 — Resource lifecycle is an architectural concern

**Status:** FOUNDATION

Temporary resources must be tracked, budgeted, and replaceable.

## ADR-024 — Current model names do not belong in the core architecture

**Status:** FOUNDATION

Current provider/model choices live in the resource/model registry.

## ADR-025 — Azure is burst capital

**Status:** DECISION

Azure credits may accelerate the system but must not be a permanent architectural dependency.

---

# 70. Current Reference Technology Candidates

These are **not frozen dependencies**.

| Function | Candidate | Status |
|---|---|---|
| Model gateway | LiteLLM | Candidate |
| Free model primary | Gemini free tier | Candidate |
| Free fast lane | Groq | Candidate |
| Additional free lane | Mistral / Cloudflare / Cerebras | Candidate |
| Local model runtime | Ollama | Candidate |
| Coding harness | Aider | Candidate |
| Free daily harness | Gemini CLI | Candidate |
| Multi-agent substrate | OpenHands | Candidate |
| MCP/automation substrate | Goose | Candidate |
| Sandbox | Docker / OS-level sandbox | Experiment |
| Local state | SQLite | Candidate |
| Durable state | PostgreSQL | Candidate |
| CI/CD | GitHub Actions | Candidate |
| Persistent CPU | Oracle Always Free | Candidate |
| Serverless | Cloudflare Workers | Candidate |
| Frontend deployment | Vercel / Netlify | Candidate |
| Monitoring | Sentry / New Relic | Candidate |
| Secrets | Doppler / 1Password | Candidate |

The candidate list must be periodically revalidated because the research itself demonstrates that free-tier availability changes rapidly.

---

# 71. What We Still Refuse to Do

Even after incorporating the research, the infrastructure will not:

- hard-code today's free models;
- assume today's free tiers will exist tomorrow;
- treat leaked Claude Code source as current truth;
- copy proprietary implementation;
- make one open-source harness the entire platform;
- expose unrestricted host execution;
- store provider state as the only copy;
- activate every student trial immediately;
- burn Azure credits merely because they exist;
- build project-specific infrastructure into the core;
- optimize benchmarks at the expense of operational reliability.

---

# 72. Immediate Phase 0 Work Queue

The next work is now concrete.

### P0-01 — Formal Architecture Map

Create the authoritative component diagram and dependency graph.

### P0-02 — Task Contract

Define what a Task is.

### P0-03 — Agent Contract

Define what an Agent is and what lifecycle state it owns.

### P0-04 — Runtime Contract

Define the exact Runtime interface.

### P0-05 — Model Contract

Define the normalized model request/response interface.

### P0-06 — Router Contract

Define routing inputs, outputs, policies, and fallback behavior.

### P0-07 — Context Contract

Define context objects, sources, ranking, compaction, and persistence.

### P0-08 — Event Contract

Define event types, schema, ordering, replay, and idempotency.

### P0-09 — Permission Contract

Define capabilities, policies, approval, and deny precedence.

### P0-10 — Sandbox Contract

Define isolation boundaries and runtime integration.

### P0-11 — Resource Registry

Define the resource lifecycle schema.

### P0-12 — Security Threat Model

Model prompt injection, malicious repositories, tool abuse, credential exposure, supply-chain attacks, and destructive actions.

### P0-13 — Cost Model

Define token, provider, runtime, quota, and resource accounting.

### P0-14 — Architecture Review

Attempt to break the design before writing implementation code.

---

# 73. Final Phase 0 Rule

The infrastructure is not ready for implementation until its major boundaries survive deliberate attack.

We should actively ask:

```text
What happens if the model disappears?

What happens if the provider changes its API?

What happens if the runtime dies?

What happens if the sandbox fails?

What happens if a tool returns 100 MB?

What happens if the agent loops?

What happens if a child agent fails?

What happens if a secret is requested?

What happens if the cloud account expires?

What happens if Azure reaches $0?

What happens if the database disappears?

What happens if the user resumes six months later?

What happens if an external document contains malicious instructions?
```

If the answer is:

> "The project breaks."

then the architecture has failed.

If the answer is:

> "Capability degrades, state survives, recovery is possible, and the failed component can be replaced."

then the architecture is doing its job.

---

# 74. Version History — Updated

## v0.2 — Research-Integrated Architecture

Added and refined:

- hybrid agent loop;
- tool taxonomy and deferred tool loading;
- context-as-resource model;
- repository understanding strategies;
- compaction and thrashing protection;
- multi-tier memory;
- session/checkpoint separation;
- multi-agent isolation;
- runtime categories;
- separated capability/policy/approval/sandbox model;
- lifecycle hooks;
- portable skills;
- provider volatility strategy;
- capability pinning;
- dual-homing;
- cache-aware routing;
- model specialization;
- total infrastructure ownership of agent state;
- resource lifecycle and claim-vs-activation model;
- Azure burst-capital strategy;
- free-backbone strategy;
- student/startup resource separation;
- free-tier failure assumptions;
- cost modes;
- resource economics;
- expanded observability;
- artifact/audit model;
- disaster-recovery classes;
- dependency rules;
- core/adapter boundary;
- component ownership matrix;
- research-to-architecture traceability;
- revised ADRs;
- candidate technology registry;
- expanded Phase 0 work queue.

**Next revision target:** v0.3 after completion of the formal component contracts and architecture/dependency graph.
