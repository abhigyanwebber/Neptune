# Session Contract

**Status:** FROZEN — architectural boundary

## Purpose
Represent a resumable execution boundary for an agent working on a task.

## Responsibilities
- identify the task/agent execution lineage;
- contain ordered turns;
- reference relevant context/checkpoints;
- provide a stable correlation boundary for model/tool activity.

## Non-responsibilities
- selecting providers;
- implementing the model;
- replacing persistent memory;
- directly executing tools.

## Invariants
1. A session belongs to one task execution lineage.
2. Turns are ordered within a session.
3. Session identity survives model/provider switching.
4. Session recovery must not depend exclusively on provider-side state.

## Deferred
- exact session persistence;
- concurrency model;
- session branching semantics.
