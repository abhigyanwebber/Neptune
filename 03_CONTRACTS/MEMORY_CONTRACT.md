# Memory Contract

**Status:** FROZEN — architectural boundary

## Purpose
Persist intentionally retained information beyond immediate model context.

## Responsibilities
- store scoped memory;
- associate memory with its namespace;
- support retrieval by authorized consumers;
- distinguish persistent information from transient context.

## Non-responsibilities
- deciding every piece of information to store;
- replacing current context;
- storing raw secrets by default.

## Invariants
1. Project memory is namespace-isolated.
2. Not all context becomes memory.
3. Memory must have provenance sufficient to support later evaluation.

## Deferred
- memory extraction algorithm;
- retrieval algorithm;
- decay/expiry policy;
- vector vs relational implementation.
