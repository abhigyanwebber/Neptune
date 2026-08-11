# Reference Component Graph

**Status:** NORMATIVE FOR FIRST IMPLEMENTATION

```text
                    +----------------------+
                    | Consuming Project    |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Neptune API / CLI     |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Task / Session App    |
                    +----+----+----+--------+
                         |    |    |
              +----------+    |    +----------------+
              |               |                     |
              v               v                     v
        +-----------+   +-----------+        +-------------+
        | Context   |   | Execution |        | Checkpoint  |
        | Manager   |   | Engine    |        | Service     |
        +-----+-----+   +-----+-----+        +------+------+ 
              |               |                     |
              +---------------+---------------------+
                              |
                              v
                     +------------------+
                     | Model Gateway    |
                     +--------+---------+
                              |
                              v
                     +------------------+
                     | Policy Router    |
                     +--------+---------+
                              |
                              v
                     +------------------+
                     | LiteLLM /        |
                     | Provider Adapter |
                     +--------+---------+
                              |
                  +-----------+-----------+
                  |           |           |
                  v           v           v
               Free       Fallback     Cheap /
               lanes      lanes        escalation

Execution Engine -> Permission Engine -> Sandbox -> Tool
       |                |                    |
       +----------------+--------------------+
                        |
                        v
                 Event / Usage Layer
                        |
                        v
                 PostgreSQL State
```

## Boundary rules

- API/CLI never imports provider SDKs.
- Core domain never imports infrastructure implementations.
- Model Gateway is the only inference boundary.
- Tool execution is downstream of permission and sandbox checks.
- PostgreSQL is the first durable state authority.
- Events are emitted at meaningful lifecycle boundaries.
- Registry data controls external resource selection.
