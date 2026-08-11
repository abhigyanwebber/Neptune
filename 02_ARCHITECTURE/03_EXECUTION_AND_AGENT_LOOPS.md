# Execution and Agent Loops

The research identified three loop families:

1. **Plan → Execute → Verify** — strong for bounded tasks.
2. **Iterative observe/reason/act loops** — strong for interactive coding.
3. **Event-stream/platform loops** — strongest for observability and programmability.

The infrastructure uses a hybrid:

```text
TASK
 ↓
PLAN
 ↓
ITERATIVE EXECUTION
 ↓
OBSERVE
 ↓
VERIFY
 ↓
CHECKPOINT / EVENT
 ↓
 ┌───────────────┐
 │               │
FAILURE       PROGRESS
 │               │
RECOVER        CONTINUE
 │               │
 └──────→───────┘
 ↓
COMPLETE / SUSPEND / ESCALATE
```

## Recovery invariants

- A failed model call must not destroy task state.
- A failed tool call must produce a classified error.
- Oversized output must be bounded.
- A repeated loop must be detectable.
- A runtime failure must permit restoration from checkpoint/state.
- Child-agent failures must be isolated from the parent task.
- Provider failure must be recoverable through routing/fallback where possible.
