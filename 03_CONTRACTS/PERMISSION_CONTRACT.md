# Permission Contract

**Status:** FROZEN — architectural contract

## Purpose
Determine whether a requested capability/operation is authorized.

## Responsibilities
- evaluate policy;
- distinguish allow/ask/deny outcomes;
- enforce higher-priority restrictions;
- provide an auditable decision.

## Non-responsibilities
- performing the operation;
- implementing the sandbox;
- deciding model routing.

## Invariants
1. Security decisions must not depend solely on model instructions.
2. A deny rule must be able to prevent execution.
3. Capability, authorization, approval, and isolation remain distinct concepts.

## Deferred
- policy language;
- exact precedence implementation;
- approval object/lifetime;
- resource-level matching.
