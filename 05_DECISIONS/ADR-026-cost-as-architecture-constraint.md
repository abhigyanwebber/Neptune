# ADR-026 — Cost Is a Core Architectural Constraint

**Status:** FROZEN  
**Scope:** Phase 0

## Context

The infrastructure is intended to be production-capable while operating on a free-or-cheap budget.

The project has access to legitimate student benefits, free tiers, and temporary cloud credits, but these resources can expire, change, or become unavailable.

## Decision

Cost and resource durability are architectural selection criteria.

The architecture will therefore:

- keep external dependencies replaceable;
- distinguish durable free resources from constrained and temporary resources;
- support a $0 baseline where technically practical;
- use temporary credits for high-value bursts rather than foundational assumptions;
- permit small paid dependencies when they materially improve production feasibility;
- track operational burden alongside financial cost.

## Consequences

Positive:

- lower recurring expenditure;
- stronger resilience to provider changes;
- easier migration;
- better use of student/cloud benefits;
- architecture remains viable after temporary credits expire.

Negative:

- more abstraction;
- more provider adapters;
- potentially lower optimization for any one provider;
- additional operational decision-making.

## Not decided here

This ADR does not select providers, services, models, or exact pricing thresholds.
