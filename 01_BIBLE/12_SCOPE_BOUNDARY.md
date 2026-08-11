# Phase 0 Scope Boundary

**Status:** FROZEN

This document exists to stop the Infrastructure Bible from becoming a disguised implementation project.

## Phase 0 must define

- vision;
- architectural layers;
- component boundaries;
- ownership;
- dependency direction;
- core domain relationships;
- major invariants;
- security boundaries;
- provider/resource independence;
- major research-derived decisions;
- what is explicitly deferred.

## Phase 0 must not build

- the final agent runtime;
- the final router;
- the final context engine;
- the final memory system;
- the final sandbox;
- production databases;
- production deployment;
- a complete MCP catalog;
- every provider adapter;
- project-specific workflows.

## The test

If a detail can be changed without changing the architecture, it belongs in a later phase.

If changing a detail would violate a documented architectural boundary, it belongs in Phase 0.

## Why this boundary exists

Complexity is useful when it represents real system structure.

Complexity becomes scope creep when we solve implementation problems before the architecture requires those solutions.

The goal is therefore:

> **complete enough to constrain implementation; incomplete enough to leave implementation freedom.**
