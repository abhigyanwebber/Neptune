# Phase 0 Validation Checklist

Phase 0 is complete when architectural ambiguity is reduced to intentional implementation freedom.

## Required now — architecture

- [x] Six-layer architecture defined
- [x] Core/adapters boundary defined
- [x] Dependency direction defined
- [x] Task → Agent → Session → Turn relationship defined
- [x] Tool → Permission → Sandbox boundary defined
- [x] Model → Gateway → Provider boundary defined
- [x] Runtime vs durable state boundary defined
- [x] Git vs checkpoint distinction defined
- [x] Project memory isolation defined
- [x] Durable vs expiring resource boundary defined
- [x] Research vs architecture authority defined
- [x] Scope boundary defined
- [x] Production/economic objective defined
- [x] Reference production blueprint defined
- [x] Resource portfolio integrated from research
- [x] Model supply topology integrated from research
- [x] Implementation readiness gate defined

## Required now — contracts

- [x] Task responsibility boundary
- [x] Agent responsibility boundary
- [x] Session responsibility boundary
- [x] Runtime responsibility boundary
- [x] Model boundary
- [x] Router boundary
- [x] Context boundary
- [x] Tool boundary
- [x] Permission boundary
- [x] Sandbox boundary
- [x] Memory boundary
- [x] Checkpoint boundary
- [x] Artifact boundary
- [x] Resource boundary
- [x] Provider boundary
- [x] Observability boundary

## Required now — source discipline

- [x] Original reports preserved
- [x] Research synthesis preserved
- [x] Research-to-architecture traceability preserved
- [x] Current provider/resource information separated from architecture
- [x] Explicit deferred-scope document exists

## Intentionally deferred

- [ ] exact method signatures
- [ ] exact database schema
- [ ] exact router scoring algorithm
- [ ] exact context ranking algorithm
- [ ] exact memory retrieval algorithm
- [ ] final sandbox implementation
- [ ] full permission DSL
- [ ] detailed multi-agent coordination
- [ ] production deployment topology
- [ ] exhaustive provider adapters
- [ ] performance optimization

These are not Phase 0 failures. They are Phase 1+ work.

## Final gate

Before Phase 1, perform a short architecture attack:

1. Remove the primary model provider.
2. Remove the runtime.
3. Expire Azure credits.
4. Kill a running session.
5. Replay a task from durable state.
6. Present a malicious external document to the agent.
7. Attempt a forbidden tool operation.
8. Start a second project and verify memory isolation.

The question is:

> Does the architecture still hold?

If yes, Phase 0 is sufficient.
