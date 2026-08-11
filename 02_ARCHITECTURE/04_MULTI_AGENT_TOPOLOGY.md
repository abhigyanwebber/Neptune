# Multi-Agent Topology

Multi-agent execution is a capability, not the default.

```text
                    COORDINATOR
                        |
          +-------------+-------------+
          |             |             |
       PLANNER        WORKER       REVIEWER
          |             |             |
       Context A     Context B     Context C
          |             |             |
       Tools A       Tools B       Tools C
          |             |             |
       Worktree A    Worktree B    Worktree C
          +-------------+-------------+
                        |
                 STRUCTURED RESULTS
                        |
                    COORDINATOR
```

## Isolation

A child agent receives:

- explicit task identity;
- bounded context;
- bounded tools;
- bounded permissions;
- optional isolated worktree/runtime.

The parent should normally receive a structured result or summary rather than every child tool call.

## Parallelism

Parallel mutable work should use separate worktrees/sandboxes unless an explicit coordination protocol exists.
