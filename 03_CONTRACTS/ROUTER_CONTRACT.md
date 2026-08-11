# Router Contract

**Status:** FROZEN — architectural contract

## Purpose
Select an appropriate model/provider for a model request.

## Responsibilities
- evaluate capability requirements;
- consider availability/health;
- consider quota and cost constraints;
- support fallback/escalation;
- preserve provider independence;
- expose the selection decision for observability.

## Non-responsibilities
- executing the model request itself;
- owning agent memory;
- implementing model-specific prompting;
- defining project requirements.

## Invariants
1. Routing is capability-oriented, not hard-coded to one provider.
2. A failed provider must have a defined degradation/fallback path where alternatives exist.
3. Model switching should respect session/context/cache boundaries.

## Deferred
- exact scoring formula;
- weighting;
- health algorithm;
- cache-cost model;
- final fallback policy.
