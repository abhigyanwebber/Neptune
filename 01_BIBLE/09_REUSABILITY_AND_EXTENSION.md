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
