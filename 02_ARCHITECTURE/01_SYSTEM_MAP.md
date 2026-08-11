# System Map

## Logical layers

```mermaid
flowchart TB
    P[Future Projects
Argus / Workspace OS / Other]
    L0[ L0 Resource Layer
Providers / Compute / Storage / Deployment]
    L1[ L1 Intelligence Layer
Model Registry / Gateway / Router / Quota / Fallback]
    L2[ L2 Agent Layer
Task / Agent / Orchestration / Planning / Delegation / Recovery]
    L3[ L3 Execution Layer
Tools / MCP / Git / Filesystem / Browser / Sandbox]
    L4[ L4 State Layer
Tasks / Sessions / Events / Context / Memory / Checkpoints]
    L5[ L5 Operations Layer
Security / Secrets / Observability / CI/CD / Backup / Lifecycle]

    P --> L2
    P --> L4
    L2 --> L1
    L2 --> L3
    L2 --> L4
    L3 --> L5
    L4 --> L5
    L1 --> L0
    L3 --> L0
    L4 --> L0
    L5 --> L0
```

## Core invariant

The project layer must not directly depend on provider-specific resources.

```text
Project
  ↓
Infrastructure contracts
  ↓
Adapters
  ↓
External resources
```

The inverse dependency is prohibited.

## Runtime execution path

```text
Task
 ↓
Coordinator / Agent Runtime
 ↓
Context Manager
 ↓
Model Gateway
 ↓
Router
 ↓
Provider / Model
 ↓
Model decision
 ↓
Permission Engine
 ↓
Sandbox
 ↓
Tool
 ↓
External effect
 ↓
Observation
 ↓
State + Event Store
 ↓
Verification
 ↓
Checkpoint / Recovery / Completion
```
