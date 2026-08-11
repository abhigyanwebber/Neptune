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
