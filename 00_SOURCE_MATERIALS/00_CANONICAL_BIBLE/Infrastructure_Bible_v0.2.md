# Infrastructure Bible

## Reusable Agentic AI Infrastructure --- Phase 0

**Document status:** Draft v0.4\
**Phase:** 0 --- Architecture Specification / Research-Integrated Design\
**Purpose:** Source of truth for the reusable infrastructure layer that
will support future projects such as Argus, Workspace OS, and other
agentic systems.

------------------------------------------------------------------------

# 0. Document Control

## 0.1 Purpose

This document defines the architecture, boundaries, principles,
contracts, and roadmap for a reusable agentic AI infrastructure stack.

The infrastructure is intentionally **project-agnostic**. Projects
consume the infrastructure; they do not define it.

The core objective is to build a durable system around replaceable
external resources:

-   model providers
-   cloud providers
-   databases
-   agent runtimes
-   tools
-   compute
-   deployment platforms

The architecture should survive the replacement or disappearance of any
individual provider.

## 0.2 Source Basis

This first draft is derived primarily from the research reports already
produced for this infrastructure effort:

1.  **Research Brief 02 --- Free / Low-Cost LLM Infrastructure for
    Agentic Coding**
2.  **Claude Code Alternatives and the Agentic Coding Harness
    Landscape**
3.  **Student Developer Benefits & Free Infrastructure Research Report**

The reports establish several important conclusions:

-   a single free-model endpoint is not a reliable architectural
    dependency;
-   a router-fronted, multi-provider model supply chain is preferred;
-   the agent harness is at least as strategically important as the
    model supply;
-   context management, tool reliability, routing, permissions,
    sandboxing, and recovery are first-class concerns;
-   free/student infrastructure is useful but must be separated into
    durable backbone resources and expiring credits;
-   the user's laptop is a support/control node rather than a primary
    large-model inference server;
-   open agent substrates such as OpenHands are useful candidates for
    multi-agent execution;
-   Git, checkpoints, event streams, MCP, and sandboxing provide
    important building blocks.

Where this document introduces a design decision that was not explicitly
established by the reports, it is marked as a **Design Decision** or
**Proposed** rather than presented as a research finding.

## 0.3 Status Vocabulary

-   **FOUNDATION** --- architectural rule that should be treated as
    stable.
-   **DECISION** --- deliberate design choice.
-   **PROPOSED** --- current design, subject to validation.
-   **EXPERIMENTAL** --- must be tested before becoming infrastructure.
-   **EXTERNAL** --- supplied by an outside service/project.
-   **DEFERRED** --- intentionally not being built yet.

------------------------------------------------------------------------

# 1. Vision

## 1.1 Core Vision

Build a reusable **Agent Infrastructure Platform** capable of running,
coordinating, observing, and controlling AI agents across multiple
models, providers, tools, runtimes, and projects.

The system should make the following replaceable:

> model, provider, runtime, cloud, database, tool, deployment platform,
> and project.

The system should make the following durable:

> interfaces, state model, orchestration model, security model, context
> model, routing abstraction, observability model, and operational
> contracts.

## 1.2 The Fundamental Principle

**The resources are replaceable. The architecture is the asset.**

We do not optimize the infrastructure around whichever free model or
cloud service happens to be available today.

Instead:

``` text
Project
   ↓
Agent Infrastructure
   ↓
Abstractions
   ↓
Replaceable Resources
```

Never:

``` text
Project
   ↓
Provider-specific implementation
```

------------------------------------------------------------------------

# 2. Strategic Objectives

## O1 --- Provider Independence

No core subsystem should require one specific model provider.

The infrastructure must support multiple providers through an
abstraction layer.

## O2 --- Model Efficiency

Use inexpensive/free models for routine work and reserve stronger models
for tasks that genuinely require them.

## O3 --- Agent Reliability

Agents must have:

-   checkpoints
-   recovery
-   verification
-   observable execution
-   bounded permissions
-   resumable state

## O4 --- Execution Safety

Agent capabilities must be separated from authorization to use those
capabilities.

Where possible, security must be enforced structurally through
sandboxing rather than relying only on prompts or user toggles.

## O5 --- Persistent State

Agent sessions, events, checkpoints, task state, and relevant memory
must survive individual model calls and runtime failures.

## O6 --- Reusability

A future project should be able to consume the infrastructure without
modifying its core internals.

## O7 --- Cost Awareness

The infrastructure must measure:

-   tokens
-   model usage
-   provider usage
-   retries
-   latency
-   runtime
-   estimated cost
-   quota consumption

## O8 --- Operational Resilience

Provider outages, quota exhaustion, model retirement, and temporary
infrastructure failure must degrade capability rather than destroy the
system.

------------------------------------------------------------------------

# 3. Non-Goals

The infrastructure will **not** initially attempt to:

-   train a frontier model;
-   build a new browser engine;
-   build a new Git implementation;
-   replace mature cloud platforms;
-   clone Claude Code feature-for-feature;
-   create a universal autonomous super-agent;
-   hard-code Argus-specific research logic;
-   hard-code Workspace OS-specific SaaS logic;
-   make Azure the permanent foundation;
-   make any single model provider indispensable.

------------------------------------------------------------------------

# 4. Architecture Overview

The system is divided into six logical layers.

``` text
L0 — RESOURCE LAYER
Cloud / compute / providers / storage / external services

L1 — INTELLIGENCE LAYER
Model registry / gateway / routing / quotas / fallback

L2 — AGENT LAYER
Agent lifecycle / orchestration / planning / delegation / recovery

L3 — EXECUTION LAYER
Tools / MCP / filesystem / shell / Git / browser / sandbox

L4 — STATE LAYER
Tasks / sessions / events / context / memory / checkpoints

L5 — OPERATIONS LAYER
Security / secrets / observability / CI/CD / backups / lifecycle
```

Future applications sit above the infrastructure:

``` text
                 FUTURE PROJECTS
          ┌──────────┼───────────┐
          ↓          ↓           ↓
        Argus    Workspace OS   Other
          └──────────┼───────────┘
                     ↓
             AGENT INFRASTRUCTURE
```

------------------------------------------------------------------------

# 5. L0 --- Resource Layer

The resource layer contains external resources that the infrastructure
consumes.

## 5.1 Resource Categories

### Compute

-   local laptop
-   free cloud CPU
-   temporary cloud CPU
-   GPU notebook environments
-   burst GPU/cloud resources

### Model Providers

-   free providers
-   cheap providers
-   frontier providers
-   local models

### Storage

-   local filesystem
-   SQLite
-   PostgreSQL
-   object storage where required

### Deployment

-   serverless
-   PaaS
-   persistent VMs
-   container environments

### Supporting Services

-   Git hosting
-   monitoring
-   secrets
-   authentication
-   DNS/CDN
-   CI/CD

## 5.2 Durable vs Expiring Resources

Resources are divided into:

### Durable Backbone

Resources suitable for long-term architecture.

Examples include:

-   GitHub
-   GitHub Actions
-   free PaaS/serverless layers
-   free database tiers
-   persistent low-cost/free CPU
-   renewable student benefits
-   multiple free inference providers

### Expiring Ammunition

Resources whose availability or credits should never become
architectural dependencies.

Examples:

-   Azure credits
-   temporary cloud trials
-   promotional model credits
-   GPU credits
-   startup credits
-   time-limited database credits

### Rule

**An expiring resource may accelerate the infrastructure, but its
disappearance must not invalidate the infrastructure.**

------------------------------------------------------------------------

# 6. L1 --- Intelligence Layer

## 6.1 Purpose

The intelligence layer abstracts all model inference from the rest of
the system.

The agent should communicate with a model abstraction, not directly with
a provider.

``` text
Agent
  ↓
Model Gateway
  ↓
Router
  ↓
Provider
  ↓
Model
```

## 6.2 Model Gateway

**FOUNDATION**

The gateway is the single logical entry point for model inference.

Responsibilities:

-   normalize model requests;
-   resolve capability requirements;
-   route requests;
-   apply quotas;
-   handle retries;
-   perform provider failover;
-   collect usage telemetry;
-   expose consistent interfaces to agents.

The initial implementation is expected to use **LiteLLM** as an external
gateway component.

This is an implementation choice, not an architectural dependency.

## 6.3 Model Registry

**PROPOSED**

A registry describing available models by capability rather than by
brand.

Example:

``` yaml
capability: fast_general
models:
  - provider_a/model_x
  - provider_b/model_y
```

Potential capability classes:

-   fast_general
-   coding
-   reasoning
-   planning
-   summarization
-   classification
-   tool_use
-   vision
-   embedding
-   frontier_escalation

The registry must record:

-   model identifier
-   provider
-   capabilities
-   context limits
-   structured-output support
-   tool-calling support
-   availability
-   cost class
-   quota
-   health
-   preferred use cases

## 6.4 Routing

**FOUNDATION**

Routing should consider:

``` text
task type
+
capability
+
provider health
+
quota
+
latency
+
cost
+
failure history
```

The router should prefer the cheapest adequate model.

It should not use a frontier model merely because one is available.

## 6.5 Escalation

Hard tasks may escalate from:

``` text
free → cheap → strong → frontier
```

Escalation should be deliberate.

Examples:

-   difficult architectural decisions;
-   long-horizon planning;
-   repeated failure;
-   stuck-turn recovery;
-   high-risk code changes;
-   complex debugging.

## 6.6 Model Switching Rule

**FOUNDATION**

Do not switch providers unnecessarily during an active reasoning chain.

Model switching should preferably happen at:

-   task boundaries;
-   checkpoints;
-   context-compaction boundaries;
-   explicit escalation points.

This prevents context and reasoning continuity from being unnecessarily
damaged.

------------------------------------------------------------------------

# 7. L2 --- Agent Layer

## 7.1 Agent Definition

An agent is a runtime entity that:

1.  receives a task;
2.  constructs or receives context;
3.  reasons using a model;
4.  invokes capabilities;
5.  observes results;
6.  updates state;
7.  verifies progress;
8.  recovers from failure;
9.  completes, pauses, or escalates.

## 7.2 Agent Lifecycle

``` text
CREATED
   ↓
INITIALIZED
   ↓
PLANNING
   ↓
EXECUTING
   ↓
VERIFYING
   ↓
 ┌─┴───────────────┐
 ↓                 ↓
SUCCESS          RECOVERY
                    ↓
                 EXECUTING
```

Possible terminal states:

-   completed
-   failed
-   cancelled
-   suspended

## 7.3 Agent Runtime Abstraction

**PROPOSED**

The infrastructure should expose a runtime-neutral interface:

``` text
create()
start()
pause()
resume()
terminate()
send()
observe()
checkpoint()
restore()
fork()
```

Possible implementations:

-   OpenHands runtime
-   Docker runtime
-   local CLI runtime
-   future runtimes

The runtime implementation must not leak into project-level logic.

## 7.4 Multi-Agent Architecture

Multi-agent execution is supported conceptually but should not be the
first implementation milestone.

Potential roles:

``` text
Planner
Worker
Reviewer
Researcher
Debugger
Verifier
Coordinator
```

The infrastructure must support delegation without requiring every
project to use every role.

------------------------------------------------------------------------

# 8. L3 --- Execution Layer

## 8.1 Capability Model

Agents may eventually access:

-   filesystem
-   shell
-   Git
-   browser
-   web
-   MCP servers
-   APIs
-   databases
-   package managers
-   build systems
-   testing systems
-   deployment systems

These are **capabilities**.

Capability does not imply permission.

## 8.2 Execution Boundary

The intended flow is:

``` text
Agent
  ↓
Permission Policy
  ↓
Sandbox
  ↓
Tool
  ↓
External Effect
```

Not:

``` text
Agent → unrestricted host execution
```

## 8.3 MCP

MCP is treated as a major extension mechanism.

It allows external capabilities to be added without modifying the agent
core.

Examples:

``` text
MCP
├── GitHub
├── browser
├── filesystem
├── database
├── cloud
└── future services
```

MCP servers remain external components.

The infrastructure owns their lifecycle, permission integration,
configuration, and observability where appropriate.

------------------------------------------------------------------------

# 9. Permission and Policy Model

## 9.1 Principle

**Capability and authorization must be separate.**

An agent may know that a tool exists without being allowed to execute
it.

## 9.2 Policy Hierarchy

Proposed precedence:

``` text
DENY
  >
ASK
  >
ALLOW
```

Policies may exist at:

-   global
-   workspace
-   agent
-   task
-   tool
-   operation

## 9.3 Sensitive Capabilities

The following require stronger controls:

-   deleting files;
-   modifying production infrastructure;
-   database migrations;
-   secret access;
-   credential management;
-   external publishing;
-   financial actions;
-   destructive cloud operations;
-   remote Git operations.

## 9.4 Structural Enforcement

Where possible, permissions should be enforced by:

-   OS sandbox;
-   container boundary;
-   filesystem boundary;
-   network policy;
-   credential scoping;
-   tool-level policy.

Prompt instructions alone are not considered a sufficient security
boundary.

------------------------------------------------------------------------

# 10. Sandbox Layer

## 10.1 Purpose

The sandbox isolates agent execution from the host.

Potential implementation:

``` text
Host
  ↓
Container
  ↓
Agent runtime
  ↓
Worktree
```

The sandbox should eventually support:

-   filesystem isolation;
-   process isolation;
-   controlled network access;
-   resource limits;
-   disposable environments;
-   reproducible environments.

## 10.2 Trust Levels

Proposed:

### Level 0 --- Read-only

Agent can inspect but cannot mutate.

### Level 1 --- Workspace

Agent can modify an assigned workspace.

### Level 2 --- Sandbox

Agent can execute code in an isolated environment.

### Level 3 --- External

Agent can interact with external systems under explicit policy.

### Level 4 --- High Risk

Sensitive or production actions requiring explicit approval.

------------------------------------------------------------------------

# 11. Git and Worktree Model

Git is part of the execution safety model.

A serious task should follow:

``` text
Base commit
   ↓
Worktree
   ↓
Agent execution
   ↓
Tests
   ↓
Verification
   ↓
Commit
   ↓
Review
   ↓
Merge / discard
```

The infrastructure should support:

-   checkpoints;
-   rollback;
-   worktrees;
-   diffs;
-   commits;
-   branch isolation;
-   task-to-commit association.

------------------------------------------------------------------------

# 12. L4 --- State Layer

## 12.1 Unified State Model

State categories:

``` text
tasks/
sessions/
agents/
events/
checkpoints/
contexts/
memories/
artifacts/
models/
providers/
quotas/
audits/
```

## 12.2 Local Development

SQLite is the initial local state store.

## 12.3 Durable State

PostgreSQL is the initial durable/shared state target.

Potential providers:

-   Supabase
-   Neon
-   self-hosted PostgreSQL

Provider choice must remain replaceable.

------------------------------------------------------------------------

# 13. Event Model

**PROPOSED FOUNDATION**

Important operations should generate events.

Example:

``` text
task.created
agent.started
context.loaded
model.requested
model.responded
tool.requested
tool.executed
tool.failed
checkpoint.created
commit.created
verification.started
verification.passed
verification.failed
agent.paused
agent.resumed
task.completed
```

Each event should contain enough metadata to reconstruct or audit
execution.

Minimum conceptual fields:

``` text
event_id
timestamp
task_id
session_id
agent_id
event_type
payload
source
```

## 13.1 Why Events Exist

Events provide:

-   auditability;
-   replay;
-   debugging;
-   state reconstruction;
-   evaluation;
-   observability;
-   failure analysis.

------------------------------------------------------------------------

# 14. Context Engine

## 14.1 Purpose

The context engine decides what information enters a model call.

It should not simply dump the entire repository or session into the
model.

## 14.2 Context Sources

Potential sources:

``` text
system instructions
agent instructions
task
project metadata
repository map
relevant files
tool definitions
recent tool results
session history
memory
Git state
checkpoints
```

## 14.3 Context Operations

The engine should eventually support:

``` text
retrieve
rank
assemble
compress
summarize
drop
persist
restore
fork
```

## 14.4 Context Priority

Proposed default priority:

``` text
1. Current task
2. Active constraints
3. Current working state
4. Relevant files/results
5. Recent execution history
6. Project instructions
7. Long-term memory
8. Historical context
```

This ordering is provisional and must be validated experimentally.

------------------------------------------------------------------------

# 15. Memory Model

Memory is divided conceptually into:

### Working Context

Information required for the current model call.

### Session Memory

Information relevant to the current task/session.

### Persistent Memory

Information worth retaining across sessions.

### Project Memory

Information belonging to a specific consuming project.

### Infrastructure Memory

Information about infrastructure itself.

The infrastructure must not accidentally mix project memory into
unrelated projects.

------------------------------------------------------------------------

# 16. L5 --- Operations Layer

## 16.1 Secrets

The system should provide a centralized secret abstraction.

Conceptual interface:

``` text
get_secret()
request_secret()
scope_secret()
revoke_secret()
rotate_secret()
```

Agents should receive the minimum credential required for a specific
operation.

They should not receive the entire environment by default.

## 16.2 Observability

Observability must cover:

``` text
agents
tasks
model calls
tool calls
MCP calls
runtime
sandbox
database
routing
providers
CI/CD
deployments
errors
```

Potential initial services:

-   Sentry
-   New Relic

These are implementation resources, not permanent architectural
dependencies.

## 16.3 Usage Accounting

Every model call should eventually record:

``` text
provider
model
input tokens
output tokens
latency
estimated cost
quota impact
retry count
task
agent
session
```

This enables infrastructure economics analysis.

------------------------------------------------------------------------

# 17. CI/CD

GitHub Actions is the initial CI/CD backbone.

Standard pipeline:

``` text
push
 ↓
lint
 ↓
tests
 ↓
security checks
 ↓
build
 ↓
artifact
 ↓
deploy
```

Agent-created code should pass normal CI/CD gates.

Agents should not be given permission to silently bypass them.

------------------------------------------------------------------------

# 18. Deployment Architecture

## 18.1 Local Control Node

The user's laptop initially hosts:

-   development tools;
-   model gateway development;
-   local orchestration;
-   SQLite;
-   small local models;
-   infrastructure administration.

It is not the primary large-model inference server.

## 18.2 Persistent Free Compute

Oracle Always Free is a candidate for lightweight persistent
infrastructure.

## 18.3 Serverless

Cloudflare Workers is a candidate for lightweight edge/API functions.

## 18.4 Frontend

Vercel or Netlify are candidate free frontend layers.

## 18.5 Burst Compute

Azure and notebook GPU environments are temporary acceleration
resources.

They must not be required for the base system to function.

------------------------------------------------------------------------

# 19. Resource Lifecycle Policy

Every external resource should have metadata:

``` text
resource_id
provider
type
purpose
status
expiration
quota
cost
dependencies
replacement
criticality
```

## Criticality Classes

### C0 --- Optional

Loss causes no meaningful degradation.

### C1 --- Useful

Loss reduces capability but system continues.

### C2 --- Important

Loss requires fallback.

### C3 --- Critical

Loss threatens a core capability.

No external provider should ideally remain C3 indefinitely.

------------------------------------------------------------------------

# 20. Provider Failure Strategy

The infrastructure must assume:

-   providers change prices;
-   free tiers disappear;
-   models are retired;
-   quotas change;
-   APIs break;
-   accounts are suspended;
-   services experience outages.

Therefore:

``` text
Provider failure
      ↓
Health detection
      ↓
Retry if appropriate
      ↓
Fallback provider
      ↓
Capability degradation
      ↓
Operator notification
```

The desired failure mode is:

> **degraded capability, not total system failure.**

------------------------------------------------------------------------

# 21. Security Principles

## S1 --- Least Privilege

Give agents only the permissions required.

## S2 --- Sandbox First

Untrusted execution should happen inside isolation.

## S3 --- Credential Minimization

Expose only necessary secrets.

## S4 --- Auditability

Important actions should be observable.

## S5 --- Reversibility

Destructive operations should have rollback/checkpoint mechanisms
whenever practical.

## S6 --- Explicit Escalation

High-risk capabilities require stronger approval.

## S7 --- No Trust in Model Intent

The model is not a security boundary.

A capable model can still:

-   misunderstand;
-   hallucinate;
-   follow malicious instructions;
-   process prompt injection;
-   make destructive mistakes.

------------------------------------------------------------------------

# 22. Prompt Injection and Tool Security

The infrastructure must assume that external content can contain
malicious instructions.

Potential attack surfaces:

``` text
web pages
GitHub issues
README files
documents
emails
MCP responses
API responses
repository code
tool output
```

External content must therefore be treated as **data**, not trusted
instructions.

The exact implementation is deferred to the security design phase.

------------------------------------------------------------------------

# 23. Skills System

Skills are reusable behavior packages.

Proposed structure:

``` text
skills/
├── coding/
├── debugging/
├── testing/
├── git/
├── browser/
├── research/
├── deployment/
├── security/
└── project-management/
```

A skill may define:

``` text
instructions
required tools
optional tools
inputs
outputs
constraints
verification
```

Skills should be loadable without changing the agent runtime.

------------------------------------------------------------------------

# 24. Infrastructure Repository Structure

Proposed repository:

``` text
agent-infrastructure/
│
├── README.md
│
├── docs/
│   ├── VISION.md
│   ├── ARCHITECTURE.md
│   ├── DESIGN_PRINCIPLES.md
│   ├── SECURITY_MODEL.md
│   ├── RESOURCE_STRATEGY.md
│   ├── MODEL_STRATEGY.md
│   ├── AGENT_MODEL.md
│   ├── CONTEXT_MODEL.md
│   ├── STATE_MODEL.md
│   ├── RUNTIME_MODEL.md
│   ├── OPERATIONS_MODEL.md
│   └── ROADMAP.md
│
├── specs/
│   ├── model-gateway/
│   ├── router/
│   ├── model-registry/
│   ├── agent-runtime/
│   ├── context/
│   ├── state/
│   ├── events/
│   ├── tools/
│   ├── mcp/
│   ├── permissions/
│   ├── sandbox/
│   ├── skills/
│   ├── observability/
│   └── infrastructure/
│
├── providers/
│   ├── models/
│   ├── compute/
│   ├── storage/
│   └── services/
│
├── configs/
├── scripts/
├── tests/
└── experiments/
```

------------------------------------------------------------------------

# 25. Component Contract Philosophy

Every major subsystem must have a contract.

A contract should define:

``` text
PURPOSE
INPUTS
OUTPUTS
STATE OWNERSHIP
DEPENDENCIES
PERMISSIONS
FAILURE MODES
OBSERVABILITY
EXTENSION POINTS
NON-GOALS
```

A subsystem must not silently own responsibilities belonging to another
subsystem.

Example:

### Model Gateway owns

-   model invocation;
-   provider selection;
-   retries;
-   usage reporting.

### Model Gateway does NOT own

-   task planning;
-   project memory;
-   filesystem operations;
-   Git operations.

This separation prevents architectural contamination.

------------------------------------------------------------------------

# 26. Dependency Direction

The preferred dependency direction is:

``` text
Projects
   ↓
Agent APIs
   ↓
Core infrastructure interfaces
   ↓
Adapters
   ↓
External providers
```

Never:

``` text
Project
   ↓
Provider SDK
   ↓
Infrastructure
```

Provider-specific code should live at the edge.

------------------------------------------------------------------------

# 27. Proposed Core Interfaces

These are conceptual interfaces, not implementation code yet.

``` text
ModelGateway
ModelRegistry
Router
AgentRuntime
AgentOrchestrator
TaskManager
ContextManager
MemoryManager
StateStore
EventStore
CheckpointManager
ToolRegistry
MCPManager
PermissionEngine
SandboxManager
SecretManager
ArtifactManager
UsageTracker
HealthManager
```

These names are provisional and should be frozen only after the detailed
contract phase.

------------------------------------------------------------------------

# 28. Phase 0 Deliverables

Phase 0 is complete only when the following exist:

## Documentation

-   [x] Infrastructure Bible v0.1
-   [ ] Architecture specification
-   [ ] Component contracts
-   [ ] Dependency rules
-   [ ] Security model
-   [ ] Resource strategy
-   [ ] Model strategy
-   [ ] Agent model
-   [ ] Context model
-   [ ] State model
-   [ ] Runtime model
-   [ ] Operations model
-   [ ] Roadmap

## Decisions

-   [ ] Core interfaces frozen
-   [ ] External vs internal responsibilities frozen
-   [ ] Provider abstraction frozen
-   [ ] State ownership frozen
-   [ ] Security boundaries frozen
-   [ ] Initial technology choices recorded
-   [ ] Explicitly deferred technologies recorded

## Validation

-   [ ] Architecture reviewed against all research reports
-   [ ] Contradictions identified
-   [ ] Open questions recorded
-   [ ] Risk register created

------------------------------------------------------------------------

# 29. Phase 1 Preview

Phase 1 should create the actual repository skeleton.

Expected result:

``` text
agent-infrastructure/
    ↓
documentation
    ↓
interfaces
    ↓
configuration
    ↓
provider adapters
    ↓
tests
```

No major agent functionality should be implemented until the contracts
are sufficiently stable.

------------------------------------------------------------------------

# 30. Current Architecture Decisions

  -----------------------------------------------------------------------
  ID                      Decision                Status
  ----------------------- ----------------------- -----------------------
  ADR-001                 Infrastructure is       FOUNDATION
                          project-agnostic        

  ADR-002                 Multi-provider model    FOUNDATION
                          abstraction is          
                          mandatory               

  ADR-003                 Model gateway sits      FOUNDATION
                          between agents and      
                          providers               

  ADR-004                 Free/expiring resources FOUNDATION
                          cannot become hard      
                          dependencies            

  ADR-005                 Agent execution must    FOUNDATION
                          pass through policy and 
                          execution boundaries    

  ADR-006                 Sandbox is preferred    FOUNDATION
                          for untrusted execution 

  ADR-007                 Git/checkpoints are     FOUNDATION
                          part of agent           
                          reliability             

  ADR-008                 State is centralized    FOUNDATION
                          behind an abstraction   

  ADR-009                 Events are first-class  PROPOSED
                          execution records       

  ADR-010                 MCP is a major          FOUNDATION
                          extension mechanism     

  ADR-011                 OpenHands is an initial PROPOSED
                          multi-agent substrate   
                          candidate               

  ADR-012                 LiteLLM is an initial   PROPOSED
                          model gateway candidate 

  ADR-013                 SQLite is initial local PROPOSED
                          state storage           

  ADR-014                 PostgreSQL is initial   PROPOSED
                          durable state target    

  ADR-015                 Laptop is a             FOUNDATION
                          control/support node,   
                          not primary large-model 
                          compute                 
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 31. Open Questions

These must not be silently decided.

### Architecture

1.  What exact interface should every agent runtime implement?
2.  Should orchestration be event-driven, request-driven, or hybrid?
3.  How much of the OpenHands runtime should be adopted versus wrapped?
4.  What belongs in the core versus adapters?

### Context

5.  What context ranking algorithm should be used?
6.  What triggers compaction?
7.  What memory should be persistent?
8.  How should project memory be isolated?

### Models

9.  What exact routing policy should be implemented first?
10. How should model capability be evaluated?
11. How should provider health be scored?
12. What is the escalation threshold?

### Security

13. What exact sandbox technology becomes the default?
14. How should network permissions work?
15. How should secrets be scoped?
16. What actions require human approval?

### State

17. How should events map to materialized state?
18. How should checkpoints be represented?
19. What must survive runtime destruction?
20. What data should be retained or discarded?

### Operations

21. How should provider quota be tracked?
22. What constitutes a provider outage?
23. How should the system degrade?
24. What must be backed up?

------------------------------------------------------------------------

# 32. Phase 0 Principle

The most important rule for the next stage is:

> **Do not code around unresolved architectural boundaries.**

If we cannot answer:

``` text
Who owns this?
Who can call this?
What does it accept?
What does it return?
What happens when it fails?
Where is its state?
How is it observed?
How can it be replaced?
```

then the subsystem is not ready to implement.

------------------------------------------------------------------------

# 33. Version History

## v0.1 --- Initial Infrastructure Bible

Established:

-   project-independent vision;
-   six-layer architecture;
-   resource strategy;
-   model gateway concept;
-   routing concept;
-   agent runtime abstraction;
-   execution/security boundaries;
-   state/event model;
-   context architecture;
-   MCP extension model;
-   observability requirements;
-   CI/CD principles;
-   repository structure;
-   Phase 0 deliverables;
-   initial ADRs;
-   open architectural questions.

Next revision should convert these concepts into formal component
contracts and architecture decision records.


---

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


---

# 75. v0.3 Scope Discipline

This revision intentionally does not turn the Bible into a complete implementation specification.

The purpose of v0.3 is to make architectural boundaries sufficiently explicit while preserving implementation freedom.

The authoritative Phase 0 additions are:

- `02_ARCHITECTURE/06_CORE_DOMAIN_MODEL.md`
- `02_ARCHITECTURE/07_BOUNDARY_RULES.md`
- `03_CONTRACTS/00_CONTRACT_CONVENTIONS.md`
- `01_BIBLE/12_SCOPE_BOUNDARY.md`
- `00_SOURCE_MATERIALS/BUILD_AUTHORITY.md`
- `12_VALIDATION/04_DEFERRED_SCOPE.md`
- `12_VALIDATION/05_FOREIGN_AGENT_HANDOFF.md`

The existing report-derived architecture remains the source basis. No current provider, runtime, cloud resource, or implementation technology is promoted to an architectural dependency merely by appearing in the research.


---

# 76. v0.4 — Production Feasibility and Economic Constraint

The infrastructure's primary objective is now explicitly recorded as:

> Build the strongest production-capable reusable agentic infrastructure that is realistically feasible to operate for free or at very low recurring cost.

This is a core architectural constraint.

The new authoritative documents are:

- `01_BIBLE/02_PRODUCTION_AND_ECONOMIC_OBJECTIVE.md`
- `01_BIBLE/13_ARCHITECTURAL_SUCCESS_CRITERIA.md`
- `05_DECISIONS/ADR-026-cost-as-architecture-constraint.md`
- `05_DECISIONS/ADR-027-temporary-resources-are-burst-capital.md`
- `06_REGISTRIES/RESOURCE_ECONOMIC_CLASSIFICATION.md`
- `12_VALIDATION/06_COST_AND_FEASIBILITY_ATTACK.md`

This revision does not select additional providers or technologies. It only makes the production/economic objective an explicit architectural criterion.


---

# v0.5 — Neptune Reference Implementation Baseline

The infrastructure is named **Neptune**.

The project objective is to build production-capable reusable agent infrastructure using the strongest feasible free/cheap resource portfolio.

The three research reports are now integrated into a concrete reference baseline:

- a model gateway and router in front of multiple free/cheap inference lanes;
- a durable free infrastructure backbone;
- temporary credit/burst capacity;
- explicit cost and quota accounting;
- provider/model registries;
- implementation-facing resource and model catalogs;
- a reference deployment topology;
- an implementation-readiness gate.

The reference baseline is documented in:

- `01_BIBLE/14_REFERENCE_PRODUCTION_BLUEPRINT.md`
- `01_BIBLE/15_IMPLEMENTATION_READINESS.md`
- `02_ARCHITECTURE/08_REFERENCE_DEPLOYMENT_TOPOLOGY.md`
- `02_ARCHITECTURE/09_MODEL_SUPPLY_TOPOLOGY.md`
- `02_ARCHITECTURE/10_RESOURCE_PLACEMENT.md`
- `06_REGISTRIES/RESOURCE_PORTFOLIO.md`
- `06_REGISTRIES/MODEL_SUPPLY_CATALOG.md`
- `08_OPERATIONS/06_COST_BUDGETING.md`
- `12_VALIDATION/07_IMPLEMENTATION_READINESS_ATTACK.md`

Provider and quota facts remain snapshots. The architecture is the durable asset; resources are replaceable.
