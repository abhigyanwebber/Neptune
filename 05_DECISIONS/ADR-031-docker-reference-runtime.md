# ADR-031 — Docker as Reference Runtime

**Status:** REFERENCE IMPLEMENTATION DECISION — REVERSIBLE
## Decision
Docker is the first reference sandbox/runtime implementation.

## Rationale
The research identified containerized runtimes as a practical isolation substrate and specifically identified OpenHands' Docker runtime as a strong experimental foundation.

## Consequence
Runtime policy remains separate from the Docker implementation so a stronger isolation technology can replace it later.

## Authority clarification

This is a first-build implementation choice, not a frozen architectural dependency. The implementation agent may replace it when a better option satisfies Neptune's architecture, production requirements, security constraints, and free/cheap objective. Any material replacement should be recorded in development state or an ADR as appropriate.
