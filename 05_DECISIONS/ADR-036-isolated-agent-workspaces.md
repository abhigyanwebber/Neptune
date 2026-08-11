# ADR-036 — Isolated Local Workspaces for Parallel Claude Development

**Status:** FROZEN DEVELOPMENT METHODOLOGY  
**Scope:** Neptune construction process

## Decision

Claude A and Claude B must use separate local Git working copies while contributing to the same canonical GitHub repository.

Example:

```text
Neptune-A → worker/claude-a
Neptune-B → worker/claude-b
```

## Rationale

A shared writable directory creates unnecessary risks:

- concurrent file modification;
- branch switching collisions;
- uncommitted-change contamination;
- ambiguous ownership;
- accidental overwrites.

Separate working copies preserve parallelism while GitHub remains the shared coordination and integration surface.

## Consequence

The human operator must provide two local workspaces and configure each Claude account's MCP filesystem access to its corresponding workspace where possible.

This is a development-process decision, not a Neptune runtime architecture decision.
