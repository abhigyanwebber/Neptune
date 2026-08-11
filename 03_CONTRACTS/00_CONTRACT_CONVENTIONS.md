# Contract Conventions

**Status:** FROZEN FOR PHASE 0

Contracts define architectural boundaries. They are not complete implementation specifications.

## Every contract must answer

1. Purpose
2. Responsibilities
3. Non-responsibilities
4. Inputs
5. Outputs
6. State owned
7. State consumed
8. Dependencies
9. Permissions
10. Failure/recovery boundary
11. Events/observability
12. Security constraints
13. Replacement strategy

## Architectural contract vs implementation contract

An architectural contract states:

- what a component means;
- what it owns;
- what it guarantees;
- what it must not do;
- what other components may expect.

An implementation contract may later add:

- exact method signatures;
- classes;
- protocols;
- serialization;
- database mapping;
- concurrency primitives.

Phase 0 defines the first category.

## Invariants

Contracts may contain **invariants**. An invariant is a rule implementation must preserve.

Examples:

- provider-specific state cannot be the only copy of durable agent state;
- tool availability does not grant permission;
- project memory is isolated by namespace;
- runtime destruction must not destroy durable task identity;
- external providers are replaceable.

## Open questions

A contract may contain an explicit `Deferred` section.

An unresolved implementation detail must not be silently converted into a frozen architectural rule.

## Status labels

- `FOUNDATION` — architecture-level invariant.
- `FROZEN` — decided for this phase.
- `PROPOSED` — current design, subject to later validation.
- `DEFERRED` — intentionally postponed.
