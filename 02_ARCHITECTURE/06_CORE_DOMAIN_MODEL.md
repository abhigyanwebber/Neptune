# Core Domain Model

**Status:** ARCHITECTURAL FOUNDATION

This document defines the minimum domain relationships that implementation must preserve.

It is deliberately a domain model, not a database schema.

## Canonical relationship

```text
Project
  │
  └── Task
       │
       ├── Agent
       │    │
       │    └── Session
       │         │
       │         └── Turn
       │              ├── Model Request / Response
       │              ├── Tool Calls
       │              └── Events
       │
       ├── Child Tasks
       ├── Checkpoints
       └── Artifacts
```

## Supporting domains

```text
Model Registry ──> Model Gateway ──> Provider
                                      │
                                      └── Model

Tool Registry ──> Tool
                     │
                     └── Permission / Sandbox

Task / Agent / Session
          │
          ├── Context
          ├── Memory
          ├── Events
          ├── Checkpoints
          └── Artifacts

Resource Registry ──> External Resource
```

## Entity meanings

### Project

A namespace belonging to a consuming application.

The infrastructure does not define project business logic.

### Task

A durable unit of requested work.

A task may have parent/child relationships and may be executed by one or more agent sessions over time.

### Agent

A runtime actor assigned to perform work on a task.

An agent has a role and a runtime binding, but does not own provider infrastructure or project policy.

### Session

A resumable execution conversation/state boundary for an agent working on a task.

A session may contain many turns.

### Turn

One model/tool interaction cycle within a session.

A turn is not necessarily identical to a single model API request because tool loops may involve multiple tool operations before the next model response.

### Event

An immutable record of a significant occurrence.

Events provide operational history and may be used to reconstruct or audit state.

### Context

The information assembled for a model interaction.

Context is derived from task state, instructions, relevant project information, tools, memory, history, and execution state.

### Memory

Persisted information intended to remain useful beyond the immediate context window.

Memory is scoped and must not silently cross project boundaries.

### Checkpoint

A recoverable execution snapshot. It is distinct from Git history.

### Artifact

A durable output of execution such as a patch, report, build artifact, or other declared result.

### Model

A capability provider used for inference. Model identity is resource metadata, not a core architectural dependency.

### Provider

An external service or local runtime that exposes one or more models.

### Tool

A capability an agent can request.

Tool availability does not imply permission.

### Permission

A policy decision governing whether a capability/operation may be performed.

### Sandbox

The execution boundary in which a permitted operation runs.

### Resource

Any external or local infrastructure dependency tracked by the resource lifecycle system.

## Required relationships

Implementation must preserve these relationships:

1. Every Task has a stable identity.
2. Every Agent belongs to a Task execution context.
3. Every Session belongs to an Agent and Task.
4. Every Turn belongs to a Session.
5. Model calls and tool calls are attributable to a Turn or its execution context.
6. Significant lifecycle changes produce Events.
7. Checkpoints refer to the execution state they represent.
8. Artifacts are attributable to the Task/session that produced them.
9. Model selection occurs through the model abstraction/gateway.
10. Tool execution passes through the execution/permission boundary.
11. Project memory is namespaced.
12. Provider-specific state must not be the only recoverable copy of agent state.

## Deliberately unspecified

This document does not define:

- table names;
- ORM;
- database vendor;
- class names;
- API endpoints;
- serialization format beyond existing schemas;
- exact event projection implementation.

Those are implementation decisions.
