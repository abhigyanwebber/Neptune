# ADR Index

## Architectural decisions

- ADR-001 — Provider independence
- ADR-002 — Project-agnostic infrastructure
- ADR-003 — Model Gateway abstraction
- ADR-004 — Capability-based model registry
- ADR-005 — Cheapest adequate model
- ADR-006 — Explicit escalation
- ADR-007 — Capability vs permission separation
- ADR-008 — Sandbox-first execution
- ADR-009 — Persistent infrastructure-owned state
- ADR-010 — Git and checkpoints are complementary
- ADR-011 — Multi-agent optionality
- ADR-012 — Event records as first-class state
- ADR-013 — Resource lifecycle
- ADR-014 — Expiring resources are acceleration, not foundation
- ADR-015 — Azure as burst capital
- ADR-016 — Hybrid agent loop
- ADR-017 — Context as managed resource
- ADR-018 — Deferred tool definitions
- ADR-019 — Agent state is infrastructure-owned
- ADR-020 — Permission and sandbox are separate
- ADR-021 — Events are first-class infrastructure state
- ADR-022 — Multi-agent execution is optional
- ADR-023 — Resource lifecycle is architectural
- ADR-024 — Current model names do not belong in core architecture
- ADR-025 — Azure is burst capital
- ADR-026 — Cost is an architectural constraint
- ADR-027 — Temporary resources are burst capital

## Reference implementation / operational decisions

These are intentionally reversible and do not override the implementation-choice authority.

- ADR-028 — Reference production stack
- ADR-029 — Reference implementation stack
- ADR-030 — PostgreSQL as first durable state
- ADR-031 — Docker reference runtime
- ADR-032 — Model Gateway and LiteLLM boundary
- ADR-033 — One provider before multi-provider resilience
- ADR-034 — $0 baseline as release gate
- ADR-035 — Two-agent Neptune development methodology
- ADR-036 — Isolated agent workspaces
- ADR-037 — Core Runtime open-source evaluation
- ADR-038 — Runtime Driver policy
- ADR-039 — Resolution layer provider selection policy
- ADR-040 — Plan executor policy
- ADR-041 — Registry canonical source
- ADR-042 — ToolPort attribution seam (B-006 finding)
- ADR-043 — Observation feedback format

When a reference implementation choice is replaced, preserve the architectural contract and record the replacement decision.
