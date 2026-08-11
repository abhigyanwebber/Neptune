# ADR-030 — PostgreSQL as First Durable State

**Status:** REFERENCE IMPLEMENTATION DECISION — REVERSIBLE
## Decision
Use PostgreSQL as the first durable implementation for task, session, event, checkpoint, artifact metadata, usage, and resource state.

## Rationale
A single durable relational authority reduces moving parts while satisfying the event/state/checkpoint requirements. Managed PostgreSQL and self-hosted PostgreSQL remain interchangeable through the repository layer.

## Consequence
The first implementation does not require a separate cache or broker merely to prove correctness.

## Authority clarification

This is a first-build implementation choice, not a frozen architectural dependency. The implementation agent may replace it when a better option satisfies Neptune's architecture, production requirements, security constraints, and free/cheap objective. Any material replacement should be recorded in development state or an ADR as appropriate.
