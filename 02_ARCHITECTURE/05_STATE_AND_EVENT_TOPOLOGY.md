# State and Event Topology

```text
                         TASK
                          |
             +------------+------------+
             |            |            |
           SESSION      MEMORY      ARTIFACTS
             |            |            |
        CHECKPOINT      CONTEXT      GIT
             |            |            |
             +------------+------------+
                          |
                       EVENTS
                          |
                  EVENT / AUDIT STORE
```

## Distinction

- **Git** = artifact/version memory.
- **Checkpoint** = execution memory.
- **Event stream** = operational history.
- **Memory** = durable knowledge/instructions.
- **Context** = information assembled for the next model call.

None is a replacement for the others.
