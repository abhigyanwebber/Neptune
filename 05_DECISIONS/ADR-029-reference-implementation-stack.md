# ADR-029 — Reference Implementation Stack

**Status:** REFERENCE IMPLEMENTATION DECISION — REVERSIBLE
## Decision
Use Python, FastAPI, Pydantic, PostgreSQL, SQLAlchemy, Docker, LiteLLM, GitHub Actions, and structured telemetry as the first reference implementation stack.

## Rationale
These choices provide a coherent, inexpensive implementation path while preserving adapters around every external dependency.

## Consequence
The first build is concrete enough to start immediately. These technologies are not elevated to architectural dependencies.

## Authority clarification

This is a first-build implementation choice, not a frozen architectural dependency. The implementation agent may replace it when a better option satisfies Neptune's architecture, production requirements, security constraints, and free/cheap objective. Any material replacement should be recorded in development state or an ADR as appropriate.
