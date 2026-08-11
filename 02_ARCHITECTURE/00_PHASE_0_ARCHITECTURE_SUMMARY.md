# Phase 0 Architecture Summary

```text
PROJECT
  ↓
TASK
  ↓
AGENT
  ↓
SESSION
  ↓
TURN
  ├── CONTEXT → MODEL GATEWAY → ROUTER → PROVIDER → MODEL
  ├── TOOL REQUEST → PERMISSION → SANDBOX → TOOL
  └── EVENTS → DURABLE EVENT HISTORY

TASK
  ├── CHECKPOINTS
  └── ARTIFACTS

INFRASTRUCTURE
  ├── MEMORY
  ├── RESOURCE REGISTRY
  ├── OBSERVABILITY
  └── OPERATIONS
```

## Architectural spine

The minimum execution spine is:

```text
Task
 → Agent
 → Session
 → Turn
 → Context
 → Model
 → Capability request
 → Permission
 → Sandbox
 → Tool
 → Observation
 → Event
 → checkpoint/recovery or next turn
```

This is the part of the architecture that must remain coherent across implementation choices.

Everything else is an extension around this spine.
