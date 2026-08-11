# Checkpoint Contract

**Status:** FROZEN — architectural boundary

## Purpose
Represent recoverable execution state at a meaningful point in a task/session.

## Responsibilities
- identify the execution snapshot;
- associate it with task/session/agent state;
- support restoration where the runtime permits;
- preserve enough metadata to understand what was checkpointed.

## Non-responsibilities
- replacing Git history;
- storing every transient process detail;
- choosing the runtime.

## Invariants
1. Git history and checkpoints are complementary.
2. Checkpoint restoration must not silently cross project namespaces.
3. A checkpoint belongs to an identifiable execution lineage.

## Deferred
- exact snapshot contents;
- storage format;
- restoration algorithm.
