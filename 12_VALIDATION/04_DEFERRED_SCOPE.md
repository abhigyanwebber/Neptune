# Deferred Scope Register

This register now describes implementation work that is intentionally not part of the first vertical slice. It is no longer a reason to delay the Bible.

## Phase 1 — reference implementation after the first vertical slice

- second/third provider adapters;
- richer quota accounting;
- provider health scoring;
- advanced routing weights;
- context retrieval/ranking;
- sophisticated compaction;
- artifact object storage;
- advanced sandbox hardening;
- deployment automation;
- backup automation;
- local-model support;
- additional MCP/tool adapters.

## Phase 2 — advanced experimentation

- routing experiments;
- cache-aware routing;
- runtime comparisons;
- sandbox comparison;
- retrieval/ranking experiments;
- model portfolio optimization.

## Phase 3 — multi-agent

- coordinator/worker protocol;
- child-agent isolation;
- parallel worktrees;
- delegation/review patterns;
- multi-agent event aggregation.

## Explicitly outside Neptune core

- project-specific Argus infrastructure;
- project-specific Workspace OS infrastructure;
- proprietary model training;
- universal cloud-management platform;
- custom auth/billing platform;
- complete MCP catalog.

## Rule

A deferred item may be promoted only by an explicit phase decision or ADR.

Do not turn implementation convenience into architectural dependency.
