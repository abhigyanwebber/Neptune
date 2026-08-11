# Architectural Boundary Rules

**Status:** FROZEN FOR PHASE 0

These rules are intended to prevent scope drift and accidental coupling.

## Boundary 1 — Project vs Infrastructure

Projects may depend on infrastructure interfaces.

Infrastructure must not import project-specific business logic.

## Boundary 2 — Core vs Provider

Core components describe capabilities and contracts.

Provider-specific SDKs belong in adapters.

A provider disappearing must not require rewriting core domain logic.

## Boundary 3 — Agent vs Model

Agents request inference through the model abstraction.

Agents do not contain provider-specific routing logic.

## Boundary 4 — Agent vs Tools

Agents request capabilities.

Tools perform capabilities.

The agent does not bypass the tool/permission boundary to perform arbitrary external effects.

## Boundary 5 — Capability vs Permission

A tool can exist without an agent being authorized to use it.

## Boundary 6 — Permission vs Sandbox

Permission answers:

> May this operation occur?

Sandbox answers:

> Where and under what execution constraints may it occur?

Neither replaces the other.

## Boundary 7 — Runtime vs State

A runtime may maintain runtime-local state, but durable agent/task/session state belongs behind the infrastructure state boundary.

Destroying a runtime must not make the task permanently unrecoverable.

## Boundary 8 — Git vs Checkpoint

Git records artifact/version history.

Checkpoints record execution recovery state.

They are complementary.

## Boundary 9 — Context vs Memory

Context is what is assembled for a model interaction.

Memory is what is intentionally persisted for future use.

Not every context item becomes memory.

## Boundary 10 — Research vs Architecture

Research can recommend.

An explicit architecture decision freezes.

A research update does not silently change the architecture.

## Boundary 11 — Durable vs Expiring Resources

Temporary credits may accelerate workloads.

Core operation must not depend on their continued existence.

## Boundary 12 — Observability vs Business Logic

Observability records execution.

It must not become the hidden source of business/task semantics.

## Boundary 13 — Security vs Model Instruction

Security policy must be enforceable outside the model.

A model instruction is not a security boundary.

## Boundary 14 — Core vs Implementation Detail

The Bible freezes externally meaningful behavior and ownership.

It deliberately does not freeze internal algorithms unless required to preserve architecture.
