# Resource Contract

**Status:** FROZEN — architectural boundary

## Purpose
Track external/local infrastructure resources and their lifecycle.

## Responsibilities
- identify resource/provider;
- track eligibility/activation/status;
- track quota/expiration where applicable;
- record criticality and replacement path.

## Non-responsibilities
- hard-coding provider APIs into core;
- guaranteeing third-party availability;
- silently activating expiring benefits.

## Invariants
1. Expiring resources cannot become hidden hard dependencies.
2. Resource state is operational metadata.
3. Provider replacement is expected.

## Deferred
- lifecycle automation;
- billing integration;
- provider-specific discovery APIs.
