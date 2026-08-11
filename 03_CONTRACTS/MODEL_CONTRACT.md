# Model Contract

**Status:** FROZEN — architectural contract

## Purpose
Provide a provider-neutral inference boundary.

## Responsibilities
- accept normalized model requests;
- return normalized model results/errors;
- expose required capability metadata;
- report usage information when available.

## Non-responsibilities
- task planning;
- memory ownership;
- tool execution;
- project logic;
- provider-specific lifecycle.

## Invariants
1. Core agents do not require a specific provider SDK.
2. Model identity is registry/resource metadata.
3. Durable agent state is not provider-owned.

## Deferred
- exact request/response schema beyond the current draft;
- streaming protocol;
- provider-specific feature negotiation.
