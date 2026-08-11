# Provider Contract

**Status:** FROZEN — architectural boundary

## Purpose
Represent an external or local provider behind a replaceable adapter.

## Responsibilities
- expose declared capabilities;
- expose health/availability information where possible;
- expose provider-specific execution through an adapter;
- report provider errors and usage metadata.

## Non-responsibilities
- defining core agent behavior;
- owning infrastructure-wide state;
- changing project architecture.

## Invariants
1. Provider adapters live at the edge.
2. Provider failure should degrade capability rather than corrupt core state.
3. Provider-specific SDKs must not leak into core interfaces.

## Deferred
- adapter interface signatures;
- provider health scoring;
- discovery implementation.
