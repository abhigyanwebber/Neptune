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
