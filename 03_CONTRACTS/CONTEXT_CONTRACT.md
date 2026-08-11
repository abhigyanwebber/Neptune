# Context Contract

**Status:** FROZEN — architectural contract

## Purpose
Assemble the information supplied to a model interaction.

## Responsibilities
- gather eligible context sources;
- respect context budgets;
- preserve required task/constraint information;
- support compression/compaction;
- expose provenance of included context where practical.

## Non-responsibilities
- permanently storing all information;
- deciding project business logic;
- executing tools;
- replacing memory storage.

## Invariants
1. Context is a managed resource, not an unbounded transcript.
2. Current task and active constraints cannot be silently evicted.
3. Tool output must be bounded or compressible.
4. Context assembly remains independent of a particular model provider.

## Deferred
- retrieval/ranking algorithm;
- token budgeting formula;
- exact compaction trigger;
- repository indexing technology.
