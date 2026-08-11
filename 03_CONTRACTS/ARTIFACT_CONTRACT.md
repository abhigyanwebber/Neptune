# Artifact Contract

**Status:** FROZEN — architectural boundary

## Purpose
Represent durable outputs produced by infrastructure execution.

## Responsibilities
- identify an artifact;
- associate it with task/session/agent provenance;
- preserve declared artifact metadata;
- support retrieval by authorized consumers.

## Non-responsibilities
- deciding project business meaning;
- replacing source control;
- storing unlimited transient logs.

## Invariants
1. Artifacts are attributable to the execution that produced them.
2. Sensitive artifacts are subject to policy.
3. Artifact storage is replaceable.

## Deferred
- storage backend;
- retention policy;
- content-addressing strategy.
